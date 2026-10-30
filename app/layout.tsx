import type { Metadata } from 'next';
import './styles.css';
export const metadata: Metadata = { title: 'Thai Dub Studio — Test Site', description: 'เว็บไซต์ทดสอบแปลและพากย์วิดีโอภาษาไทย' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="th"><body>{children}</body></html>;
}
