import React, { useState } from "react";
import { 
  BookOpen, 
  Cpu, 
  Bell, 
  Scale, 
  TrendingUp, 
  Bot, 
  Activity, 
  HelpCircle, 
  ChevronDown, 
  ChevronRight, 
  ShieldAlert, 
  Key, 
  Terminal,
  FileText,
  Sliders,
  DollarSign,
  Newspaper
} from "lucide-react";

type DocSection = "intro" | "setup" | "modules" | "faq";

export function DocsPanel() {
  const [activeSection, setActiveSection] = useState<DocSection>("intro");
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const toggleFaq = (index: number) => {
    setOpenFaq(openFaq === index ? null : index);
  };

  const sections = [
    { id: "intro", label: "Pengantar & Arsitektur", icon: BookOpen },
    { id: "setup", label: "Panduan Setup & API", icon: Key },
    { id: "modules", label: "Panduan Fitur & Modul", icon: FileText },
    { id: "faq", label: "FAQ & Troubleshooting", icon: HelpCircle },
  ];

  const faqs = [
    {
      q: "Mengapa tes Telegram Alert memunculkan status FAILED (400) 'chat not found'?",
      a: "Error ini terjadi ketika Anda belum menekan tombol '/start' pada Bot Telegram Anda. Cari username Bot Telegram Anda di aplikasi Telegram, buka obrolan baru dengan Bot tersebut, klik tombol Start (atau ketik '/start'), lalu coba klik 'Kirim Alarm Tes' kembali di panel pengaturan."
    },
    {
      q: "Bagaimana cara kerja fitur Veto Gate (Out-of-Distribution Guard)?",
      a: "Veto Gate adalah lapisan perlindungan risiko cerdas yang membandingkan kondisi pasar saat ini dengan rentang distribusi data historis (OOD limits). Jika parameter volatilitas, rasio volume, atau korelasi aset melampaui batas wajar, Veto Gate akan langsung membatalkan eksekusi sinyal beli/jual otomatis dari LLM demi melindungi portofolio Anda dari kondisi pasar abnormal."
    },
    {
      q: "Apakah simulasi perdagangan di platform ini menggunakan dana riil?",
      a: "Tidak. Seluruh transaksi di platform KriptoSakti (baik manual maupun otomatis melalui AI Bot) bersifat simulasi menggunakan Demo Wallet dengan saldo awal virtual sebesar $100.000. Fitur ini dirancang murni untuk keperluan latihan, analisis, dan pengujian strategi."
    },
    {
      q: "Bagaimana perbedaan antara model AI/LLM dengan ML Lokal?",
      a: "AI/LLM (seperti Gemini) digunakan untuk memahami dan menganalisis berita kualitatif, rilis geopolitik, dan data makroekonomi untuk menilai sentimen pasar. Sementara ML Lokal (seperti Random Forest/XGBoost) dilatih secara lokal menggunakan data harga historis kuantitatif untuk memprediksi arah pergerakan harga lilin berikutnya (Candlestick) berdasarkan indikator teknikal."
    }
  ];

  return (
    <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 shadow-2xl min-h-[600px] flex flex-col lg:flex-row gap-6">
      
      {/* Sidebar Navigation */}
      <div className="lg:w-1/4 flex flex-row lg:flex-col gap-2 border-b lg:border-b-0 lg:border-r border-slate-800/80 pb-4 lg:pb-0 lg:pr-4 overflow-x-auto whitespace-nowrap lg:whitespace-normal">
        <div className="hidden lg:flex items-center gap-2 px-3 py-2 mb-4">
          <Terminal className="h-5 w-5 text-indigo-400" />
          <span className="font-sans font-bold text-white text-sm tracking-wide">PANDUAN KriptoSakti</span>
        </div>
        {sections.map((sec) => {
          const IconComponent = sec.icon;
          const isActive = activeSection === sec.id;
          return (
            <button
              key={sec.id}
              onClick={() => setActiveSection(sec.id as DocSection)}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-xs font-bold transition font-sans cursor-pointer ${
                isActive 
                  ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20" 
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/30"
              }`}
            >
              <IconComponent className="h-4 w-4" />
              <span>{sec.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      <div className="lg:w-3/4 lg:pl-2 flex-grow overflow-y-auto max-h-[650px] pr-2">
        {activeSection === "intro" && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h3 className="font-sans font-bold text-white text-lg flex items-center gap-2 mb-2">
                <BookOpen className="h-5 w-5 text-indigo-400" />
                Tentang KriptoSakti Terminal
              </h3>
              <p className="text-slate-400 text-xs leading-relaxed font-sans">
                KriptoSakti Terminal adalah platform simulasi perdagangan kripto canggih yang memadukan analisis berita berbasis Model Bahasa Besar (LLM), prediksi machine learning lokal, pengujian strategi historis (backtesting), serta simulasi eksekusi langsung. Platform ini dirancang untuk melatih kemampuan analisis pasar secara menyeluruh tanpa risiko finansial.
              </p>
            </div>

            <div className="border-t border-slate-800/60 pt-6">
              <h4 className="font-sans font-bold text-white text-sm mb-4">Arsitektur & Alur Kerja Sinyal</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-sans">
                <div className="bg-slate-950/40 border border-slate-800/80 p-4 rounded-xl">
                  <div className="text-indigo-400 font-bold mb-1 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                    1. Pengumpulan Sinyal
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    Sistem melakukan scraping berita makro & geopolitik global secara real-time, lalu memformatnya untuk dianalisis oleh AI.
                  </p>
                </div>
                <div className="bg-slate-950/40 border border-slate-800/80 p-4 rounded-xl">
                  <div className="text-indigo-400 font-bold mb-1 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                    2. Evaluasi Veto Gate
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    Setiap rekomendasi transaksi diperiksa silang oleh pelindung OOD untuk memastikan indikator teknikal tidak berada dalam kondisi ekstrim.
                  </p>
                </div>
                <div className="bg-slate-950/40 border border-slate-800/80 p-4 rounded-xl">
                  <div className="text-indigo-400 font-bold mb-1 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                    3. Eksekusi Otomatis
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    Jika disetujui, AI Bot mengeksekusi perdagangan secara simulasi dan mengirimkan alert via Telegram secara instan.
                  </p>
                </div>
              </div>
            </div>

            <div className="border-t border-slate-800/60 pt-6">
              <h4 className="font-sans font-bold text-white text-sm mb-3">Teknologi Utama</h4>
              <ul className="space-y-2 text-xs text-slate-400 font-sans">
                <li className="flex items-start gap-2">
                  <span className="text-indigo-400 mt-0.5">•</span>
                  <span><strong>Kecerdasan Buatan (LLM):</strong> Integrasi dengan Google Gemini-3-Flash untuk melakukan ekstraksi sentimen berita makro/geopolitik dan memberikan keputusan rasional di setiap volatilitas pasar.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-indigo-400 mt-0.5">•</span>
                  <span><strong>Machine Learning Lokal:</strong> Algoritma regresi & klasifikasi yang melatih data pasar historis untuk memproyeksikan arah pergerakan lilin (candlestick).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-indigo-400 mt-0.5">•</span>
                  <span><strong>Real-time Alert Dispatcher:</strong> Menyalurkan informasi transaksi terotomatisasi secara langsung ke bot chat pribadi Anda.</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {activeSection === "setup" && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h3 className="font-sans font-bold text-white text-lg flex items-center gap-2 mb-2">
                <Key className="h-5 w-5 text-indigo-400" />
                Konfigurasi API & Integrasi Notifikasi
              </h3>
              <p className="text-slate-400 text-xs leading-relaxed font-sans">
                Sebelum memulai otomasi perdagangan, Anda disarankan untuk melakukan setup koneksi agar platform dapat terhubung dengan API kecerdasan buatan dan pengirim notifikasi.
              </p>
            </div>

            <div className="border-t border-slate-800/60 pt-6 space-y-4">
              <div className="bg-slate-950/40 border border-slate-800/80 rounded-xl p-4 font-sans text-xs">
                <h4 className="text-white font-bold mb-2 flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-indigo-400" />
                  Langkah 1: Setup Kunci API LLM (Kecerdasan Buatan)
                </h4>
                <ol className="list-decimal list-inside space-y-1.5 text-slate-400 pl-1 leading-relaxed">
                  <li>Masuk ke tab <strong>Pengaturan AI & Notif</strong>.</li>
                  <li>Pada bagian <strong>Konfigurasi AI Engine</strong>, pilih Provider AI Anda (misalnya <em>Gemini</em>).</li>
                  <li>Masukkan Kunci API (API Key) Anda di kolom yang tersedia.</li>
                  <li>Apabila Anda menggunakan router/endpoint custom, isi URL Base dan Model ID yang ditargetkan (misalnya model <code className="bg-slate-900 px-1 py-0.5 rounded text-indigo-300">ag/gemini-3-flash-agent</code>).</li>
                  <li>Klik tombol <strong>Simpan Konfigurasi AI</strong>.</li>
                </ol>
              </div>

              <div className="bg-slate-950/40 border border-slate-800/80 rounded-xl p-4 font-sans text-xs">
                <h4 className="text-white font-bold mb-2 flex items-center gap-2">
                  <Bell className="h-4 w-4 text-indigo-400" />
                  Langkah 2: Integrasi Bot Telegram Alert
                </h4>
                <ol className="list-decimal list-inside space-y-1.5 text-slate-400 pl-1 leading-relaxed">
                  <li>Buka Telegram, buat bot baru melalui <code className="bg-slate-900 px-1 py-0.5 rounded text-slate-300">@BotFather</code> untuk mendapatkan <strong>Bot Token</strong> Anda.</li>
                  <li>Dapatkan <strong>Chat ID</strong> pribadi Anda menggunakan bot seperti <code className="bg-slate-900 px-1 py-0.5 rounded text-slate-300">@userinfobot</code>.</li>
                  <li><strong>Penting:</strong> Cari username Bot Anda di Telegram dan kirim pesan <code className="bg-slate-900 px-1 py-0.5 rounded text-slate-300">/start</code> untuk memulai interaksi.</li>
                  <li>Tempelkan Token dan Chat ID Anda ke kolom isian di tab <strong>Pengaturan AI & Notif</strong> di bagian Notifikasi.</li>
                  <li>Klik <strong>Simpan Pengaturan Notifikasi</strong>.</li>
                  <li>Uji coba dengan mengklik <strong>Kirim Alarm Tes</strong> untuk mengirim sinyal uji coba langsung ke ponsel Anda.</li>
                </ol>
              </div>
            </div>
          </div>
        )}

        {activeSection === "modules" && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h3 className="font-sans font-bold text-white text-lg flex items-center gap-2 mb-2">
                <FileText className="h-5 w-5 text-indigo-400" />
                Panduan Penggunaan Modul
              </h3>
              <p className="text-slate-400 text-xs leading-relaxed font-sans">
                Berikut penjelasan ringkas tentang cara mengoperasikan dan menganalisis setiap tab modul yang tersedia di panel terminal.
              </p>
            </div>

            <div className="border-t border-slate-800/60 pt-6 grid grid-cols-1 md:grid-cols-2 gap-4 font-sans text-xs">
              <div className="bg-slate-950/30 border border-slate-850 p-4 rounded-xl">
                <div className="flex items-center gap-2 text-indigo-400 font-bold mb-2">
                  <TrendingUp className="h-4 w-4" />
                  Desk Trading
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Pusat simulasi transaksi manual. Pantau pergerakan grafik lilin real-time, lakukan transaksi instan dengan modal simulasi, dan lihat status posisi aset terbuka beserta estimasi keuntungan (unrealized PnL).
                </p>
              </div>

              <div className="bg-slate-950/30 border border-slate-850 p-4 rounded-xl">
                <div className="flex items-center gap-2 text-indigo-400 font-bold mb-2">
                  <Newspaper className="h-4 w-4" />
                  Sentimen Berita
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Scraping berita terkini dari media terpercaya. AI akan memindai kata kunci krisis geopolitik/makro dan memberikan prediksi dampak pasar kuantitatif beserta arah pergerakan harga aset-aset utama.
                </p>
              </div>

              <div className="bg-slate-950/30 border border-slate-850 p-4 rounded-xl">
                <div className="flex items-center gap-2 text-indigo-400 font-bold mb-2">
                  <Scale className="h-4 w-4" />
                  Backtester
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Uji coba efektivitas bot di masa lalu. Anda dapat menentukan parameter uji coba, memilih taktik trading (Martingale, Arbitrase, Konservatif), lalu meninjau grafik performa saldo, win rate, dan penarikan modal maksimum (maximum drawdown).
                </p>
              </div>

              <div className="bg-slate-950/30 border border-slate-850 p-4 rounded-xl">
                <div className="flex items-center gap-2 text-indigo-400 font-bold mb-2">
                  <Cpu className="h-4 w-4" />
                  AI & ML Local
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Latih model kecerdasan buatan Anda sendiri menggunakan data pasar lokal. Modul ini melacak performa klasifikasi (akurasi, F1-Score) dan memetakan variabel mana yang paling berpengaruh terhadap pergerakan harga.
                </p>
              </div>

              <div className="bg-slate-950/30 border border-slate-850 p-4 rounded-xl">
                <div className="flex items-center gap-2 text-indigo-400 font-bold mb-2">
                  <Bot className="h-4 w-4" />
                  AI Bot Auto-Trade
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Aktifkan perdagangan otomatis yang dievaluasi berkala. Bot akan mengkombinasikan penilaian sentimen berita (dari LLM) dan arah tren (dari ML lokal) dengan pembagian bobot yang dapat Anda atur secara leluasa.
                </p>
              </div>

              <div className="bg-slate-950/30 border border-slate-850 p-4 rounded-xl">
                <div className="flex items-center gap-2 text-indigo-400 font-bold mb-2">
                  <Activity className="h-4 w-4" />
                  LIVE TRADING
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Mode langsung yang mensimulasikan lingkungan trading aktif. Begitu ada berita geopolitik baru atau pergerakan tren terdeteksi, sistem akan langsung mengkalkulasi sinyal secara otomatis untuk mengeksekusi transaksi.
                </p>
              </div>
            </div>
          </div>
        )}

        {activeSection === "faq" && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h3 className="font-sans font-bold text-white text-lg flex items-center gap-2 mb-2">
                <HelpCircle className="h-5 w-5 text-indigo-400" />
                FAQ & Pemecahan Masalah
              </h3>
              <p className="text-slate-400 text-xs leading-relaxed font-sans">
                Temukan jawaban cepat atas pertanyaan dan permasalahan teknis yang paling sering dihadapi oleh pengguna terminal.
              </p>
            </div>

            <div className="border-t border-slate-800/60 pt-6 space-y-3 font-sans text-xs">
              {faqs.map((faq, index) => {
                const isOpen = openFaq === index;
                return (
                  <div 
                    key={index}
                    className="bg-slate-950/40 border border-slate-850 rounded-xl overflow-hidden transition-all duration-300"
                  >
                    <button
                      onClick={() => toggleFaq(index)}
                      className="w-full flex items-center justify-between p-4 text-left font-bold text-white cursor-pointer hover:bg-slate-800/20 transition"
                    >
                      <span>{faq.q}</span>
                      {isOpen ? (
                        <ChevronDown className="h-4 w-4 text-indigo-400" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-slate-500" />
                      )}
                    </button>
                    {isOpen && (
                      <div className="px-4 pb-4 text-slate-400 text-[11px] leading-relaxed border-t border-slate-850/60 pt-3">
                        {faq.a}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
