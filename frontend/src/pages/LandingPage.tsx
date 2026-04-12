import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '@/components/common/Navbar'
import Footer from '@/components/common/Footer'
import HeroSection from '@/components/landing/HeroSection'
import AppMockup from '@/components/landing/AppMockup'
import FeaturesSection from '@/components/landing/FeaturesSection'
import { authStore } from '@/store/auth'

export default function LandingPage() {
  const navigate = useNavigate()

  useEffect(() => {
    if (authStore.isAuthenticated()) {
      navigate('/dashboard', { replace: true })
    }
  }, [navigate])

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