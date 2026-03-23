import Navbar from '@/components/common/Navbar'
import Footer from '@/components/common/Footer'
import HeroSection from '@/components/landing/HeroSection'
import AppMockup from '@/components/landing/AppMockup'
import FeaturesSection from '@/components/landing/FeaturesSection'

export default function LandingPage() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Navbar />
      <main>
        <HeroSection />
        <AppMockup />
        <FeaturesSection />
      </main>
      <Footer />
    </div>
  )
}