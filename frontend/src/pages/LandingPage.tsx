import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '@/components/common/Navbar'
import Footer from '@/components/common/Footer'
import HeroSection from '@/components/landing/HeroSection'
import AppMockup from '@/components/landing/AppMockup'
import FeaturesSection from '@/components/landing/FeaturesSection'
import HowItWorksSection from '@/components/landing/HowItWorksSection'
import CTASection from '@/components/landing/CTASection'
import { authStore } from '@/store/auth'

export default function LandingPage() {
  const navigate = useNavigate()

  useEffect(() => {
    if (authStore.isAuthenticated()) {
      navigate('/dashboard', { replace: true })
    }
  }, [navigate])

  return (
    <div className="min-h-screen bg-bg">
      <Navbar />
      <main>
        <HeroSection />
        <AppMockup />
        <FeaturesSection />
        <HowItWorksSection />
        <CTASection />
      </main>
      <Footer />
    </div>
  )
}
