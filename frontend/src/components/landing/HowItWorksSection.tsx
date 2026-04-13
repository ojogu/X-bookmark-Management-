import { LogIn, RefreshCw, Layers, type LucideIcon } from 'lucide-react'

const steps: { number: string; icon: LucideIcon; title: string; desc: string }[] = [
  {
    number: '01',
    icon: LogIn,
    title: 'Connect',
    desc: 'Sign in with X and authorize SaveStack in a single click. No credit card required.',
  },
  {
    number: '02',
    icon: RefreshCw,
    title: 'Sync',
    desc: 'We automatically pull all your saved posts. First import takes about a minute.',
  },
  {
    number: '03',
    icon: Layers,
    title: 'Explore',
    desc: 'Search, filter by folder or tag, and rediscover everything you meant to read.',
  },
]

export default function HowItWorksSection() {
  return (
    <section className="px-4 py-24 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        {/* Heading */}
        <div className="mb-16 text-center">
          <p className="text-label mb-3 text-text-muted">How it works</p>
          <h2 className="font-serif italic text-4xl text-text-primary">
            Up and running in{' '}
            <span className="text-brand-mid">30 seconds.</span>
          </h2>
        </div>

        {/* Steps */}
        <div className="flex flex-col gap-8 md:flex-row md:gap-0">
          {steps.map((step, i) => (
            <div key={step.number} className="flex flex-1 items-start gap-0 md:flex-col md:items-center md:text-center">
              {/* Step content */}
              <div className="relative flex-1 px-0 md:flex md:w-full md:flex-col md:items-center md:px-6">
                {/* Connector line — desktop only */}
                {i < steps.length - 1 && (
                  <div className="absolute left-1/2 top-8 hidden h-px w-full translate-x-1/2 border-t border-dashed border-border-strong md:block" />
                )}

                {/* Icon circle */}
                <div className="relative mb-0 flex-shrink-0 md:mb-6">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full border border-brand/20 bg-brand-light">
                    <step.icon size={22} className="text-brand-mid" />
                  </div>
                  <span className="text-label absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-brand text-[9px] font-bold text-white">
                    {step.number.slice(1)}
                  </span>
                </div>

                {/* Text — mobile: inline, desktop: below */}
                <div className="ml-5 md:ml-0">
                  <h3 className="mb-1.5 text-base font-semibold text-text-primary">{step.title}</h3>
                  <p className="text-sm leading-relaxed text-text-secondary md:max-w-[200px]">{step.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
