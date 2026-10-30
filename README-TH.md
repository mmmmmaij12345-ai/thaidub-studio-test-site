# Thai Dub Studio — V3 (Test)

โปรเจกต์ทดสอบแยกจาก `AUTO UGC FACTORY` โดยตั้งใจทำงานเป็น 2 ส่วน: หน้าเว็บ Next.js และ Worker สำหรับประมวลผลเสียง/วิดีโอ

## ความสามารถในรุ่นนี้
- เลือกวิดีโอจากเครื่อง/โทรศัพท์
- ตรวจสถานะ Worker ผ่านปุ่ม `ตรวจการเชื่อมต่อ`
- ถอดเสียงด้วย Faster-Whisper
- แปล/ปรับบทพูดไทยผ่าน OpenRouter (ต้องใส่ API key บน Worker) หรือแก้บทภาษาไทยเอง
- เลือกเสียงไทยหญิง/ชายและความเร็วเสียง
- สร้างเสียงพากย์, ฝังซับไทย และส่งออก MP4
- ดาวน์โหลดไฟล์ซับ SRT แยก
- Worker รองรับวิดีโอไม่มีเสียงต้นฉบับ และปรับการเรนเดอร์ให้ไม่ตัดภาพตามความยาวเสียงพากย์

## สำคัญ: ต้อง deploy Worker แยก
Vercel ใช้รันหน้าเว็บ Next.js ส่วน Worker ใช้ FFmpeg, FFprobe, Faster-Whisper และ Edge TTS ซึ่งไม่ควรรันงานหนักเหล่านี้ใน Vercel Function ปกติ

### Deploy หน้าเว็บ
1. ใน GitHub ให้ `package.json`, `app/`, `next.config.mjs`, `tsconfig.json` อยู่ที่ราก Repository
2. Vercel → Settings → Build and Deployment:
   - Framework Preset: `Next.js`
   - Root Directory: เว้นว่าง/ราก Repository หาก `package.json` อยู่หน้าแรก
   - Build Command: `npm run build`
   - Install Command: `npm install`
3. Deploy
4. เมื่อ Worker พร้อมแล้ว ให้เพิ่ม Environment Variable ใน Vercel:
   - `NEXT_PUBLIC_THAI_DUB_WORKER_URL` = URL สาธารณะของ Worker เช่น `https://your-worker.example.com` (ไม่ต้องใส่ `/` ท้าย URL)
5. Redeploy หน้าเว็บหลังเพิ่ม Environment Variable

### Deploy Worker ด้วย Docker
1. ใช้ผู้ให้บริการที่รองรับ Docker และงานประมวลผลหนัก; ตั้ง Root/Build context เป็นโฟลเดอร์ `worker/` หรือให้ Dockerfile ที่ `worker/Dockerfile` ถูกใช้จากรากตามการตั้งค่าของผู้ให้บริการ
2. เปิดพอร์ตที่กำหนดโดย `PORT` (ค่าเริ่มต้น 8080)
3. ตั้ง Environment Variables ตามต้องการ:
   - `CORS_ORIGINS` = URL ของเว็บ Vercel แบบเต็ม เช่น `https://your-site.vercel.app` (หลายโดเมนคั่นด้วย comma)
   - `WHISPER_MODEL` = `small` (ดาวน์โหลดโมเดลครั้งแรก ใช้ RAM/CPU และพื้นที่ดิสก์)
   - `WHISPER_DEVICE` = `cpu`
   - `WHISPER_COMPUTE_TYPE` = `int8`
   - `MAX_UPLOAD_MB` = `300`
   - `OPENROUTER_API_KEY` = API key สำหรับแปลบท (ไม่จำเป็นหากจะพิมพ์บทไทยเอง)
   - `OPENROUTER_MODEL` = `openrouter/free` (โมเดล free routing อาจไม่พร้อม/เปลี่ยนเงื่อนไขได้)
4. ตรวจ `https://YOUR-WORKER/health` ควรคืน JSON ที่มี `"ok": true`, `"ffmpeg": true`, `"ffprobe": true`
5. ใส่ URL Worker ใน Vercel ตามขั้นตอนด้านบน แล้ว Redeploy

## ทดสอบตามลำดับ
1. เปิดเว็บ แล้วกด `ตรวจการเชื่อมต่อ` ต้องเห็น `เชื่อมต่อได้`
2. อัปโหลดวิดีโอสั้นที่มีเสียงพูด
3. กดถอดเสียง
4. กดแปล หรือกรอกบทภาษาไทยเองในแต่ละช่วง
5. เลือกเสียง แล้วสร้าง MP4
6. ตรวจภาพ เสียง ซับ และความยาวไฟล์ผลลัพธ์ก่อนใช้จริง

## ข้อจำกัดและค่าใช้จ่าย
- หน้าเว็บ Vercel อาจมี Free tier แต่ Worker สำหรับวิดีโอใช้ CPU/RAM/พื้นที่ และผู้ให้บริการอาจจำกัดเวลาหรือคิดค่าใช้จ่ายได้ จึงไม่สามารถรับรองว่าโฮสต์ Worker ฟรีตลอดไป
- Faster-Whisper ดาวน์โหลดโมเดลเมื่อใช้งานครั้งแรก จึงอาจช้าและใช้ทรัพยากรมาก
- Edge TTS เป็นบริการออนไลน์ ไม่รับประกัน SLA/ความพร้อมใช้งาน
- API key ห้ามใส่ในโค้ดหน้าเว็บหรือ commit ลง GitHub ให้ตั้งใน Environment Variables ของ Worker เท่านั้น
- การ Build และการประมวลผลวิดีโอจริงต้องทดสอบบนผู้ให้บริการปลายทางก่อนถือว่าใช้งานได้สมบูรณ์
