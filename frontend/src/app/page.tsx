"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import styles from "./page.module.css";

/* ──────────────────────────────────────
   Scroll-Reveal Hook
   ────────────────────────────────────── */
function useReveal() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add(styles.visible);
          observer.unobserve(el);
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return ref;
}

/* ──────────────────────────────────────
   Reveal Wrapper Component
   ────────────────────────────────────── */
function Reveal({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const ref = useReveal();
  return (
    <div ref={ref} className={`${styles.reveal} ${className}`}>
      {children}
    </div>
  );
}

/* ──────────────────────────────────────
   Animated Inline Icons (4-frame cycle)
   ────────────────────────────────────── */
function CyclingIcons({ icons }: { icons: string[] }) {
  return (
    <span className={styles.inlineIcons}>
      {icons.map((icon, i) => (
        <span key={i} className={styles.iconFrame}>
          {icon}
        </span>
      ))}
    </span>
  );
}

/* ──────────────────────────────────────
   Animated Brand Dots
   ────────────────────────────────────── */
function BrandDots() {
  return (
    <span className={styles.brandMark}>
      <span className={styles.brandDot} />
      <span className={styles.brandDot} />
      <span className={styles.brandDot} />
    </span>
  );
}

/* ──────────────────────────────────────
   Page
   ────────────────────────────────────── */
export default function Home() {
  return (
    <div className={styles.page}>
      {/* ── Sticky Navigation ── */}
      <nav className={styles.nav}>
        <Link href="/" className={styles.logo}>
          VÂK
        </Link>
        <Link href="/waitlist" className={styles.navButton}>
          Join waitlist
        </Link>
      </nav>

      {/* ── Hero with Rainbow Glows ── */}
      <section className={styles.hero}>
        {/* Atmospheric glow blobs */}
        <div className={styles.glowContainer}>
          <div className={styles.glow1} />
          <div className={styles.glow2} />
          <div className={styles.glow3} />
        </div>

        {/* Announcement pill */}
        <Link
          href="https://x.com"
          target="_blank"
          rel="noopener noreferrer"
          className={styles.announcementPill}
        >
          Launching on Instagram — join the early access
          <span className={styles.pillArrow}>→</span>
        </Link>

        {/* Main heading */}
        <h1 className={styles.heroHeading}>Many years ago,</h1>
      </section>

      {/* ── Manifesto Body ── */}
      <section className={styles.manifesto}>
        {/* Paragraph 1 — The promise */}
        <Reveal>
          <p className={styles.paragraph}>
            <CyclingIcons icons={["📸", "📱", "🎨", "✨"]} />
            Instagram told us: there was <em>&ldquo;a way to share your world.&rdquo;</em> And
            for a while, it felt like there was. Authentic moments. Real stories. Creative
            expression. The feed felt boundless.
          </p>
        </Reveal>

        {/* Paragraph 2 — The decay (fragmented spacing) */}
        <Reveal>
          <p className={`${styles.paragraph} ${styles.fragmented}`}>
            But year after year, our feeds became noisier.{" "}
            <br />
            <span className={styles.wideSpace}>
              Visions of authentic storytelling
            </span>{" "}
            gave way to a relentless content{" "}
            <em>treadmill</em>.{" "}
            <span className={styles.wideSpace}>
              A &nbsp;dozen &nbsp;posts &nbsp;a &nbsp;week
            </span>{" "}
            demanded &nbsp;by &nbsp;a &nbsp;handful &nbsp;of &nbsp;ever&#8209;changing &nbsp;algorithms.
          </p>
        </Reveal>

        {/* Paragraph 3 — The tension */}
        <Reveal>
          <p className={styles.paragraph}>
            And so, we spend our days. Planning shoots. Writing captions. Editing reels.
            But our creativity? It&apos;s trapped in execution. Made for algorithms. Not for{" "}
            <em>us</em>.
          </p>
        </Reveal>

        {/* Paragraph 4 — The shift */}
        <Reveal>
          <p className={styles.paragraph}>
            When your content is created by an agent oriented around <em>you…</em> It&apos;s
            freed from the exhaustion of the daily grind. Freed from staring at blank
            screens. And freed from the soul-crushing cycle of post, measure, repeat.
          </p>
        </Reveal>

        {/* Paragraph 5 — The purpose + handwriting */}
        <Reveal>
          <p className={styles.paragraph}>
            We believe social media still has a greater purpose: to help each of us share
            our stories,{" "}
            <span className={styles.handwriting}>our way</span>
          </p>
        </Reveal>

        {/* Paragraph 6 — The introduction */}
        <Reveal>
          <p className={styles.paragraph}>
            That&apos;s why we built VÂK.{" "}
            <BrandDots />
            <br />
            The first <em>autonomous</em> social media agent.
          </p>
        </Reveal>

        {/* Paragraph 7 — What it does */}
        <Reveal>
          <p className={styles.paragraph}>
            An intelligent entity based on your brand, your voice, and your visual
            language. Not just another <em>scheduling tool…</em> but this time,{" "}
            <em>an agent for you</em>.
          </p>
        </Reveal>

        {/* Paragraph 8 — How it works */}
        <Reveal>
          <p className={styles.paragraph}>
            Without rigid templates and one-size-fits-all strategies, every piece of
            content can feel… A deep understanding of your audience. An evolving memory of{" "}
            <em>your brand</em>, that makes every post feel more intentional.
          </p>
        </Reveal>

        {/* Paragraph 9 — The honest moment (bold) */}
        <Reveal>
          <p className={styles.paragraph}>
            So what will your agent create? In truth, it&apos;s hard to say.{" "}
            <strong>Because we don&apos;t know your brand yet.</strong>
          </p>
        </Reveal>

        {/* Paragraph 10 — The vision */}
        <Reveal>
          <p className={styles.paragraph}>
            But we do know this… Someday, we&apos;ll look back on manual content
            creation like we do on hand-coding HTML websites. A craft that made sense
            for its era. And that&apos;s just fine.
          </p>
        </Reveal>

        {/* Paragraph 11 — The analogy */}
        <Reveal>
          <p className={styles.paragraph}>
            We believe that a new medium of creativity is upon us… As Canva taught us
            that design can go far beyond the limited tools of Photoshop, And Notion
            showed us that <em>knowledge</em> is bigger than spreadsheets and docs, we
            believe in a future of social media that is far richer and more personal.
          </p>
        </Reveal>

        {/* Paragraph 12 — The closing thought */}
        <Reveal>
          <p className={styles.paragraph}>
            A future where your social presence is an extension of your creativity, not a
            drain on your time. Starting with Instagram, and expanding to everywhere your
            audience lives.
          </p>
        </Reveal>
      </section>

      {/* ── Closing CTA ── */}
      <Reveal>
        <section className={styles.closing}>
          <h2 className={styles.closingHeading}>
            A new era of autonomous social media is here.
          </h2>
          <Link href="/waitlist" className={styles.ctaButton}>
            Join waitlist
          </Link>
        </section>
      </Reveal>

      {/* ── Footer ── */}
      <footer className={styles.footer}>
        <Link href="/terms">Terms and Conditions</Link>
        <span className={styles.footerDot}>•</span>
        <Link href="/privacy">Privacy Policy</Link>
        <span className={styles.footerDot}>•</span>
        <span>VÂK, Inc. © {new Date().getFullYear()}</span>
      </footer>
    </div>
  );
}
