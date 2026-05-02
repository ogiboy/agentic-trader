import type { HomeContent } from '@/lib/home/content/types';

export const homeContentTr: HomeContent = {
  badges: [
    { label: 'Geliştirici Dokümanları', variant: 'secondary' },
    { label: 'Fumadocs + MDX', variant: 'outline' },
    { label: 'Local-first', variant: 'outline' },
  ],
  heroTitle: 'Operatörün gördüğü runtime gerçeğiyle aynı yerden geliştir.',
  heroDescription:
    'Agentic Trader ikinci derece bir sohbet demosu değil. Bu docs yüzeyi; inspect edilebilir depolama, açık güvenlik kapıları ve CLI, Ink, observer API ile Web GUI arasında paylaşılan sözleşmeler üzerine kurulu paper-first bir trading runtime için geliştirici yüzeyidir.',
  primaryAction: 'Dokümanları oku',
  secondaryAction: {
    href: '/docs/getting-started',
    label: 'Hızlı başlangıcı aç',
  },
  trustCards: {
    runtime: {
      title: 'Runtime öncelikli',
      body: "Bir cycle'a güvenmeden önce model servisi, runtime durumu, broker durumu ve review yüzeyleri birbiriyle uyuşmalı.",
    },
    safety: {
      title: 'Güvenlik kapılı',
      body: 'Paper execution, strict LLM gating, provider görünürlüğü ve sessiz runtime fallback yokluğu vazgeçilmezdir.',
    },
    surface: {
      title: 'Çoklu yüzey',
      body: 'CLI, Rich, Ink, observer API ve Web GUI ayrı UI doğruları üretmek yerine aynı sözleşmelerin üstünde çalışır.',
    },
  },
  currentFocusItems: [
    {
      icon: 'bot',
      text: 'İsteğe bağlı app-managed Ollama supervision mevcut daemon ve log yüzeyini genişletmeli.',
    },
    {
      icon: 'layout',
      text: '`webgui` ince bir local kabuk olarak kalırken `docs` kanonik geliştirici yüzeyi olmalı.',
    },
    {
      icon: 'inspect',
      text: 'Bootstrap, provider hazırlığı ve QA kanıtları daha standart bir onboarding yoluna taşınıyor.',
    },
  ],
  guardrail:
    'Web GUI ve docs sitesi geliştirici/operatör yüzeyleridir. Orkestrasyon sahipliği almazlar; Python runtime sözleşmeleri kaynak gerçektir.',
  entryPoints: [
    {
      href: '/docs/getting-started',
      title: 'Başlangıç',
      description:
        'Depoyu kur, doctor çalıştır, model hazırlığını doğrula ve ana operatör yüzeylerini aç.',
      badge: 'Kurulum',
    },
    {
      href: '/docs/architecture',
      title: 'Mimari',
      description:
        'Paket sahipliğini, runtime sınırlarını ve neden paralel bir orkestrasyon katmanı istemediğimizi oku.',
      badge: 'Sistem haritası',
    },
    {
      href: '/docs/runtime-and-operations',
      title: 'Runtime ve Operasyon',
      description:
        'Modları, supervision, logları, stop kontrollerini ve operatöre görünen runtime gerçeğini anla.',
      badge: 'Operasyon',
    },
    {
      href: '/docs/data-and-intelligence',
      title: 'Veri ve Zekâ Katmanı',
      description:
        "Market context, provider normalization ve feature bundle'ların agent graph'i nasıl beslediğini gör.",
      badge: 'Sinyaller',
    },
    {
      href: '/docs/frontend-system',
      title: 'Frontend Sistemi',
      description:
        "`docs` ile `webgui`yi paylaşılan shadcn preset'i, local-first monospace tipografi ve modüler dosya organizasyonu üzerinden hizalı tut.",
      badge: 'Frontend',
    },
    {
      href: '/docs/memory-and-review',
      title: 'Hafıza ve Review',
      description:
        "Docs, `.ai` notları, feedback taslakları ve review artefact'lerinin runtime gerçeğiyle nasıl hizalı kaldığını gör.",
      badge: 'Süreklilik',
    },
    {
      href: '/docs/qa-and-debugging',
      title: 'QA ve Debugging',
      description:
        'Bir değişikliği yayınlanabilir saymadan önce smoke QA, runtime kanıtı ve operatör-gerçeği kontrollerini kullan.',
      badge: 'Doğrulama',
    },
  ],
  workflowTracks: [
    {
      id: 'build',
      label: 'Geliştir',
      cards: [
        {
          title: 'Kurulum izi',
          body: 'Önce `README.md`yi oku, sonra `doctor`, local model hazırlığı ve docs hızlı başlangıcı ile ortamı doğrula.',
        },
        {
          title: 'Mimari izi',
          body: "Edit yapmadan önce en küçük sahip modülü bulmak için `dev/code-map.md` ve mimari docs'unu birlikte kullan.",
        },
        {
          title: 'Frontend izi',
          body: "`webgui` ve `docs` Next.js App Router, Tailwind v4 ve shadcn primitive'lerini paylaşır; ama erken paylaşılan paket icat etmemelidir.",
        },
      ],
    },
    {
      id: 'operate',
      label: 'İşlet',
      cards: [
        {
          title: 'Runtime modu',
          body: "Operation ve training farklı güvenlik beklentileri olan runtime overlay'leridir; iki ayrı ürün değildir.",
        },
        {
          title: 'Operatör yüzeyleri',
          body: 'CLI, Ink, Rich, observer API ve Web GUI aynı daemon, broker ve review durumunu anlatmalıdır.',
        },
        {
          title: 'Feedback akışı',
          body: 'Pages docs feedback tarayıcı içinde GitHub issue taslağı hazırlar; server-side forwarding ancak açık bir Node-hosted docs yüzeyi varsa geri gelmeli.',
        },
      ],
    },
    {
      id: 'inspect',
      label: 'İncele',
      cards: [
        {
          title: 'Review izi',
          body: 'Bir agent cevabını yeterli kanıt saymadan önce trace, review, trade context ve memory inspection yüzeylerini kullan.',
        },
        {
          title: 'Kalite izi',
          body: 'Ruff, Pytest, Pyright, smoke QA ve UI kontrollerini tek bir yeşil tik yerine katmanlı bir kalite sistemi olarak gör.',
        },
        {
          title: 'Docs izi',
          body: 'Runtime davranışı veya varsayımlar değiştiğinde `.ai/current-state.md`, `.ai/tasks.md`, `.ai/decisions.md` ve ilgili docs sayfasını birlikte güncelle.',
        },
      ],
    },
  ],
};
