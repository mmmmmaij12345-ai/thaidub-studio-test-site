import os, json, tempfile, subprocess, asyncio, shutil
from pathlib import Path
from typing import List
import requests
import edge_tts
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from faster_whisper import WhisperModel

app=FastAPI(title="Thai Dub Worker", version="1.0.0")
origins=[x.strip() for x in os.getenv("CORS_ORIGINS","*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"])
MODEL=os.getenv("WHISPER_MODEL","small")
DEVICE=os.getenv("WHISPER_DEVICE","cpu")
COMPUTE=os.getenv("WHISPER_COMPUTE_TYPE","int8")
MAX_MB=int(os.getenv("MAX_UPLOAD_MB","300"))

def ensure_ffmpeg():
    if not shutil.which("ffmpeg"): raise HTTPException(500,"ไม่พบ FFmpeg บน Worker ต้องติดตั้ง FFmpeg ก่อน")
async def save_upload(upload:UploadFile, path:Path):
    total=0
    with path.open("wb") as out:
        while True:
            chunk=await upload.read(1024*1024)
            if not chunk: break
            total+=len(chunk)
            if total>MAX_MB*1024*1024: raise HTTPException(413,f"ไฟล์ใหญ่เกิน {MAX_MB} MB")
            out.write(chunk)
    if total==0: raise HTTPException(400,"ไฟล์วิดีโอว่างเปล่า")
def whisper_model(): return WhisperModel(MODEL,device=DEVICE,compute_type=COMPUTE)
def srt_time(sec):
    ms=max(0,int(sec*1000)); h=ms//3600000; m=(ms%3600000)//60000; s=(ms%60000)//1000; ms%=1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"
def run(cmd):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode: raise RuntimeError(p.stderr[-3000:])
    return p.stdout

def media_duration(path:Path)->float:
    try:
        out=run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)])
        return max(0.0,float(out.strip()))
    except Exception:
        return 0.0

def has_audio(path:Path)->bool:
    try:
        return bool(run(["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=index","-of","csv=p=0",str(path)]).strip())
    except Exception:
        return False
@app.get("/health")
def health(): return {"ok":True,"ffmpeg":bool(shutil.which("ffmpeg")),"ffprobe":bool(shutil.which("ffprobe")),"model":MODEL}
@app.post("/transcribe")
async def transcribe(video:UploadFile=File(...)):
    ensure_ffmpeg()
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/("input"+Path(video.filename or "video.mp4").suffix)
        await save_upload(video,p)
        audio=Path(td)/"audio.wav"
        try: run(["ffmpeg","-y","-i",str(p),"-vn","-ac","1","-ar","16000",str(audio)])
        except Exception as e: raise HTTPException(400,f"อ่านเสียงจากวิดีโอไม่ได้: {e}")
        try:
            model=whisper_model(); segments,info=model.transcribe(str(audio),vad_filter=True,word_timestamps=False)
            data=[{"start":round(s.start,3),"end":round(s.end,3),"source":s.text.strip(),"thai":""} for s in segments if s.text.strip()]
            if not data: raise HTTPException(422,"ไม่พบคำพูดในวิดีโอ ลองตรวจสอบว่าไฟล์มีเสียงพูดหรือไม่")
            return {"language":info.language,"language_probability":info.language_probability,"segments":data}
        except HTTPException: raise
        except Exception as e: raise HTTPException(500,f"ถอดเสียงไม่สำเร็จ: {e}")
@app.post("/translate")
async def translate(segments:str=Form(...)):
    try: rows=json.loads(segments)
    except Exception: raise HTTPException(400,"รูปแบบ segments ไม่ถูกต้อง")
    key=os.getenv("OPENROUTER_API_KEY","").strip()
    if not key: raise HTTPException(503,"ยังไม่ได้ตั้งค่า OPENROUTER_API_KEY บน Worker คุณสามารถพิมพ์/วางบทภาษาไทยเองในหน้าเว็บได้")
    model=os.getenv("OPENROUTER_MODEL","openrouter/free")
    payload={"model":model,"temperature":0.2,"messages":[{"role":"system","content":"Translate each source speech segment into natural Thai suitable for voice dubbing. Preserve meaning, product facts, and segment order. Return ONLY a JSON array of strings with one Thai translation per input segment. Do not invent prices, features, or claims."},{"role":"user","content":json.dumps([r.get("source","") for r in rows],ensure_ascii=False)}]}
    try:
        r=requests.post("https://openrouter.ai/api/v1/chat/completions",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":os.getenv("APP_ORIGIN","https://localhost"),"X-Title":"AUTO UGC FACTORY Thai Dub"},json=payload,timeout=90)
        if not r.ok: raise HTTPException(502,f"OpenRouter ตอบกลับ HTTP {r.status_code}: {r.text[:500]}")
        content=r.json()["choices"][0]["message"]["content"]
        content=content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        out=json.loads(content)
        if not isinstance(out,list) or len(out)!=len(rows): raise ValueError("จำนวนคำแปลไม่ตรงกับจำนวนช่วงเสียง")
        for i,row in enumerate(rows): row["thai"]=str(out[i])
        return {"segments":rows}
    except HTTPException: raise
    except Exception as e: raise HTTPException(502,f"แปลไม่สำเร็จหรือผลลัพธ์ไม่ใช่ JSON: {e}")
@app.post("/render")
async def render(video:UploadFile=File(...),segments:str=Form(...),voice:str=Form("th-TH-PremwadeeNeural"),speed:float=Form(1.0),keep_original_audio:bool=Form(True),burn_subtitles:bool=Form(True)):
    ensure_ffmpeg()
    try: rows=json.loads(segments)
    except Exception: raise HTTPException(400,"รูปแบบ segments ไม่ถูกต้อง")
    if not isinstance(rows,list) or not rows or any(not str(x.get("thai","")).strip() for x in rows): raise HTTPException(400,"มีช่วงที่ยังไม่มีบทพากย์ภาษาไทย")
    allowed={"th-TH-PremwadeeNeural","th-TH-NiwatNeural"}
    if voice not in allowed: raise HTTPException(400,"เสียงที่เลือกไม่รองรับ")
    speed=max(.8,min(1.2,float(speed)))
    td=tempfile.TemporaryDirectory(); root=Path(td.name); suffix=Path(video.filename or "video.mp4").suffix.lower()
    if suffix not in {".mp4",".mov",".m4v",".webm",".mkv",".avi"}: suffix=".mp4"
    source=root/("input"+suffix)
    try:
        await save_upload(video,source)
        duration=media_duration(source)
        if duration<=0: raise HTTPException(400,"อ่านความยาววิดีโอไม่ได้ หรือไฟล์วิดีโอไม่ถูกต้อง")
        original_has_audio=has_audio(source)
        inputs=[]; filters=[]
        for i,row in enumerate(rows):
            text=str(row.get("thai","")).strip()
            start=max(0.0,float(row.get("start",0)))
            if start>=duration: continue
            audio=root/f"seg{i}.mp3"
            rate=f"{int((speed-1)*100):+d}%"
            await edge_tts.Communicate(text,voice,rate=rate).save(str(audio))
            input_index=len(inputs)//2
            inputs += ["-i",str(audio)]
            delay=max(0,int(start*1000))
            filters.append(f"[{input_index}:a]adelay={delay}|{delay},volume=1.0[a{input_index}]")
        if not inputs: raise HTTPException(400,"ไม่มีช่วงบทพากย์ที่อยู่ในความยาววิดีโอ")
        audio_count=len(inputs)//2
        mix="".join(f"[a{i}]" for i in range(audio_count))
        # Pad the dubbed track to the original video's duration so short speech never truncates the video.
        filters.append(f"{mix}amix=inputs={audio_count}:duration=longest:normalize=0,apad,atrim=duration={duration:.3f},alimiter=limit=0.95[dub]")
        dubbed=root/"dub.wav"
        run(["ffmpeg","-y",*inputs,"-filter_complex",";".join(filters),"-map","[dub]","-ac","2","-ar","44100",str(dubbed)])
        srt=root/"thai.srt"
        srt_rows=[]
        for i,x in enumerate(rows):
            a=max(0,min(duration,float(x.get("start",0)))); b=max(a,min(duration,float(x.get("end",a+1))))
            if b>a: srt_rows.append(f"{len(srt_rows)+1}\n{srt_time(a)} --> {srt_time(b)}\n{str(x.get('thai','')).strip()}")
        srt.write_text("\n\n".join(srt_rows)+"\n",encoding="utf-8-sig")
        output=root/"thai-dub-final.mp4"
        if keep_original_audio and original_has_audio:
            af="[0:a]volume=0.16[orig];[1:a]volume=1.0[dub];[orig][dub]amix=inputs=2:duration=longest:normalize=0,apad,atrim=duration="+f"{duration:.3f}"+"[aout]"
            cmd=["ffmpeg","-y","-i",str(source),"-i",str(dubbed),"-filter_complex",af,"-map","0:v:0","-map","[aout]","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-t",f"{duration:.3f}"]
        else:
            cmd=["ffmpeg","-y","-i",str(source),"-i",str(dubbed),"-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-t",f"{duration:.3f}"]
        if burn_subtitles:
            sp=str(srt).replace("\\","/").replace(":","\\:").replace("'","\\'")
            cmd += ["-vf",f"subtitles='{sp}':force_style='FontName=Noto Sans Thai,FontSize=18,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=28'"]
        cmd += [str(output)]
        run(cmd)
        from starlette.background import BackgroundTask
        return FileResponse(output,media_type="video/mp4",filename="thai-dub-final.mp4",background=BackgroundTask(td.cleanup))
    except HTTPException:
        td.cleanup(); raise
    except Exception as e:
        td.cleanup(); raise HTTPException(500,f"สร้างเสียงหรือวิดีโอไม่สำเร็จ: {e}")
