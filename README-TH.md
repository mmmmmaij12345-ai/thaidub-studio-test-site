# Thai Dub Studio — V3 (Test)

โปรเจกต์ทดสอบแยกจาก `AUTO UGC FACTORY` โดยตั้งใจทำงานเป็น 2 ส่วน: หน้าเว็บ Next.js และ Worker สำหรับประมวลผลเสียง/วิดีโอ

## ความสามารถในรุ่นนี้
- เลือกวิดีโอจากเครื่อง/โทรศัพท์
- ตรวจสถานะ Worker ผ่านปุ่ม `ตรวจการเชื่อมต่อ`
- ถอดเสียงด้วย Faster-Whisper
- แปล/ปรับบทพูดไทยผ่าน OpenRouter (ต้องใส่ API key บน Worker) หรือแก้บทภาษาไทยเอง
- คำแปลใช้บริบทข้อความข้างเคียงเป็นชุดละไม่เกิน 25 ช่วง พร้อมคงลำดับและตรวจจำนวนผลลัพธ์
- แก้ข้อความต้นฉบับ/บทไทย เพิ่มหรือลบช่วง และดาวน์โหลด SRT แบบ UTF-8
- เลือกเสียงไทยหญิง/ชายและความเร็วเสียง
- สร้างเสียงพากย์, ฝังซับไทย และส่งออก MP4
- ดาวน์โหลดไฟล์ซับ SRT แยก
- Worker รองรับวิดีโอไม่มีเสียงต้นฉบับ ตรวจว่ามีแทร็กภาพ และปรับการเรนเดอร์ให้ไม่ตัดภาพตามความยาวเสียงพากย์
- สถานะ `/health` ตรวจ FFmpeg และ FFprobe จริง; โมเดล Whisper ถูกโหลดครั้งเดียวต่อ Worker เพื่อลดเวลาและหน่วยความจำที่ใช้ซ้ำ

## สำคัญ: ต้อง deploy Worker แยก
Vercel ใช้รันหน้าเว็บ Next.js ส่วน Worker ใช้ FFmpeg, FFprobe, Faster-Whisper และ Edge TTS ซึ่งไม่ควรรันงานหนักเหล่านี้ใน Vercel Function ปกติ

## ทดลองในเครื่องก่อนเชื่อมเว็บหลัก
ต้องมี Node.js 18.17 ขึ้นไปและ Docker Desktop ที่กำลังทำงาน

1. เปิด Terminal ในโฟลเดอร์ `worker` แล้วสร้าง image: `docker build -t thai-dub-worker .`
2. รัน Worker ใน Terminal เดิม (ใส่ OpenRouter key เมื่อต้องการใช้แปลอัตโนมัติ):

   ```powershell
   docker run --rm -p 8080:8080 -v thai-dub-models:/models `
     -e CORS_ORIGINS=http://localhost:3000 `
     -e OPENROUTER_API_KEY="ใส่คีย์ของคุณ" `
     thai-dub-worker
   ```

   ทดสอบ `http://localhost:8080/health` ให้ `ok`, `ffmpeg`, `ffprobe` เป็น `true`
3. เปิด Terminal อีกหน้าต่างที่รากโปรเจกต์ แล้วรัน:

   ```powershell
   npm install
   $env:NEXT_PUBLIC_THAI_DUB_WORKER_URL = "http://localhost:8080"
   npm run dev
   ```

4. เปิด `http://localhost:3000` แล้วทำตามหัวข้อทดสอบด้านล่าง

บรรทัด `OPENROUTER_API_KEY` เป็นตัวเลือก หากไม่ใส่ยังทดสอบถอดเสียงและพิมพ์บทไทยเองเพื่อเรนเดอร์ได้ Volume `thai-dub-models` เก็บโมเดล Whisper ไว้ข้ามการปิด Worker การดาวน์โหลดโมเดลครั้งแรกอาจใช้เวลาหลายนาที

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

### แนวทางตรวจความแม่นยำ
- Whisper อาจฟังชื่อเฉพาะ ตัวเลข สำเนียง หรือเสียงทับกันผิดได้ ให้เทียบข้อความต้นฉบับกับคลิปก่อนแปล
- ผลแปลเป็นร่างภาษาไทยสำหรับพากย์ ควรตรวจคำปฏิเสธ ชื่อสินค้า/บุคคล หน่วย ตัวเลข และข้อความกล่าวอ้างก่อนเรนเดอร์
- ช่วงเสียงที่รู้จำได้เป็นช่วง ๆ อาจมีการเว้นวรรคหรือแบ่งประโยคไม่เหมาะ จึงแก้ต้นฉบับและบทแปลในหน้าเว็บได้
- API key และไฟล์วิดีโอจะถูกส่งไปยัง Worker/บริการที่ตั้งค่าไว้; อย่าใช้วิดีโอที่มีข้อมูลอ่อนไหวโดยไม่ตรวจนโยบายบริการเหล่านั้น

## ข้อจำกัดและค่าใช้จ่าย
- หน้าเว็บ Vercel อาจมี Free tier แต่ Worker สำหรับวิดีโอใช้ CPU/RAM/พื้นที่ และผู้ให้บริการอาจจำกัดเวลาหรือคิดค่าใช้จ่ายได้ จึงไม่สามารถรับรองว่าโฮสต์ Worker ฟรีตลอดไป
- Faster-Whisper ดาวน์โหลดโมเดลเมื่อใช้งานครั้งแรก จึงอาจช้าและใช้ทรัพยากรมาก
- Edge TTS เป็นบริการออนไลน์ ไม่รับประกัน SLA/ความพร้อมใช้งาน
- API key ห้ามใส่ในโค้ดหน้าเว็บหรือ commit ลง GitHub ให้ตั้งใน Environment Variables ของ Worker เท่านั้น
- การ Build และการประมวลผลวิดีโอจริงต้องทดสอบบนผู้ให้บริการปลายทางก่อนถือว่าใช้งานได้สมบูรณ์
- การแปลอัตโนมัติไม่รับประกันความถูกต้องสมบูรณ์; งานเผยแพร่หรือข้อมูลสำคัญต้องผ่านการทบทวนคน
