# Thai Dub Studio — Test Site

เว็บทดสอบแยกจาก AUTO UGC FACTORY

## โครงสร้างที่สำคัญ
- `package.json` ต้องอยู่ในโฟลเดอร์รากเดียวกับ `app/` และ `next.config.mjs`
- เว็บนี้ใช้ Next.js 14, React 18 และ TypeScript
- `worker/` เป็นบริการประมวลผลวิดีโอแยกต่างหาก ยังต้อง deploy Worker และกำหนด `NEXT_PUBLIC_THAI_DUB_WORKER_URL` ใน Vercel ก่อนใช้ฟังก์ชันถอดเสียง/แปล/เรนเดอร์จริง

## อัปโหลดไฟล์ขึ้น GitHub
แตก ZIP แล้วคัดลอก **เนื้อหาภายในโฟลเดอร์นี้** ไปยังโฟลเดอร์ local repository ที่เชื่อมกับ `thai-dub-studio-test-site` โดยตรง ให้ `package.json`, `app/`, `next.config.mjs` อยู่ระดับเดียวกัน ไม่สร้างโฟลเดอร์ซ้อน จากนั้น Commit และ Push

## ตั้งค่า Vercel
- Framework Preset: Next.js
- Root Directory: เว้นว่าง (หรือ `./`) หาก `package.json` อยู่ที่ราก repository
- Build Command: `npm run build`
- Install Command: `npm install`
- Node.js: 18.x ขึ้นไป

การแก้แพ็กเกจช่วยให้ Vercel ตรวจพบ Next.js เมื่อไฟล์นี้ถูก push ไปยังราก repository แล้ว แต่ยังต้องตรวจ Build Logs หลัง deploy จริง
