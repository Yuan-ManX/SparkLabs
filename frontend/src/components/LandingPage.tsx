import React from 'react';
import {
  Sparkles,
  Rocket,
  Zap,
  Gamepad2,
  Layers,
  Star,
  CheckCircle,
  Cpu,
  Image,
  ArrowRight,
  Code,
  Music,
  Camera,
  Globe
} from 'lucide-react';

// SparkLabs Landing Page
const LandingPage: React.FC = () => {
  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-white overflow-x-hidden">
      {/* Navigation Bar */}
      <nav className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <span className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                SparkLabs
              </span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              {['Products', 'Solutions', 'Learn', 'Pricing', 'Community'].map((item) => (
                <button
                  key={item}
                  className="text-slate-300 hover:text-white transition-colors font-medium"
                >
                  {item}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-4">
              <button className="text-slate-300 hover:text-white transition-colors font-medium">
                Sign In
              </button>
              <button className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 transition-all shadow-lg hover:shadow-purple-500/30">
                Get Started
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 overflow-hidden py-24 md:py-32">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1200px] h-[1200px] bg-gradient-to-br from-purple-900/30 to-pink-900/30 rounded-full blur-3xl" />
        <div className="max-w-7xl mx-auto px-6 text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-900/30 border border-purple-500/30 rounded-full mb-8">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span className="text-purple-300 text-sm font-semibold">AI-Powered Game Development</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-black mb-6 leading-tight">
            Build games with
            <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent ml-3">
              AI Magic
            </span>
          </h1>
          
          <p className="text-xl md:text-2xl text-slate-400 mb-10 max-w-3xl mx-auto">
            SparkLabs is the world's first AI-native game development platform. Create stunning games faster than ever before with intelligent automation and creative AI tools.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <button className="px-10 py-4 bg-gradient-to-r from-purple-600 to-pink-600 rounded-2xl font-bold text-lg hover:from-purple-700 hover:to-pink-700 transition-all shadow-xl hover:shadow-purple-500/40 flex items-center gap-2">
              Start Building Now
              <ArrowRight className="w-5 h-5" />
            </button>
            <button className="px-10 py-4 bg-slate-800 border border-slate-700 rounded-2xl font-bold text-lg hover:bg-slate-700 transition-all">
              Watch Demo
            </button>
          </div>

          <div className="relative">
            <div className="absolute -inset-8 bg-gradient-to-r from-purple-600 to-pink-600 rounded-3xl blur-2xl opacity-30" />
            <div className="relative bg-slate-900 border border-slate-700 rounded-3xl p-2 shadow-2xl">
              <div className="bg-slate-950 rounded-2xl aspect-video flex items-center justify-center text-slate-500 text-xl">
                <div className="text-center">
                  <Gamepad2 className="w-16 h-16 mx-auto text-purple-400 mb-4" />
                  Preview your game in real-time
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 md:py-32 bg-slate-950">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">Why SparkLabs?</h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              Everything you need to build professional games, powered by the most advanced AI in the industry
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: Cpu,
                title: 'AI-Powered',
                desc: 'Intelligent generation of assets, scripts, and levels. Let AI handle the heavy lifting while you focus on creativity.'
              },
              {
                icon: Layers,
                title: 'Visual Editor',
                desc: 'Drag-and-drop game design with intuitive interface. Build games visually without writing a single line of code.'
              },
              {
                icon: Zap,
                title: 'Lightning Fast',
                desc: 'Real-time preview with instant feedback. Test your changes immediately as you make them.'
              },
              {
                icon: Globe,
                title: 'Deploy Anywhere',
                desc: 'Build for web, mobile, desktop, and more. One-click exports for 25+ platforms.'
              },
              {
                icon: Image,
                title: 'Asset Library',
                desc: 'Thousands of AI-generated assets ready to use. Sprites, sounds, music, and more.'
              },
              {
                icon: Star,
                title: 'Community',
                desc: 'Join thousands of creators building amazing games. Share, learn, and collaborate!'
              }
            ].map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div
                  key={index}
                  className="p-8 bg-slate-900 border border-slate-800 rounded-3xl hover:border-purple-500/50 transition-all hover:-translate-y-1 hover:shadow-2xl"
                >
                  <div className="p-4 bg-gradient-to-br from-purple-600/20 to-pink-600/20 rounded-2xl w-fit mb-6">
                    <Icon className="w-10 h-10 text-purple-400" />
                  </div>
                  <h3 className="text-2xl font-bold mb-3">{feature.title}</h3>
                  <p className="text-slate-400 leading-relaxed">{feature.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Showcase Section */}
      <section className="py-24 md:py-32 bg-gradient-to-b from-slate-950 to-slate-900">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">Games Built with SparkLabs</h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              See what creators are building with the power of SparkLabs AI
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                title: 'Neon Quest',
                genre: 'Action Platformer',
                color: 'from-purple-600 to-pink-600'
              },
              {
                title: 'Space Odyssey',
                genre: 'Space Shooter',
                color: 'from-blue-600 to-cyan-600'
              },
              {
                title: 'Fantasy Realm',
                genre: 'RPG Adventure',
                color: 'from-green-600 to-emerald-600'
              },
              {
                title: 'Puzzle Master',
                genre: 'Puzzle Game',
                color: 'from-yellow-600 to-orange-600'
              },
              {
                title: 'Pixel Heroes',
                genre: 'Retro RPG',
                color: 'from-pink-600 to-purple-600'
              },
              {
                title: 'Cyber City',
                genre: 'Action Adventure',
                color: 'from-indigo-600 to-blue-600'
              }
            ].map((game, index) => (
              <div
                key={index}
                className="group relative overflow-hidden rounded-3xl bg-slate-800 border border-slate-700 hover:shadow-2xl hover:-translate-y-2 transition-all"
              >
                <div className={`h-48 bg-gradient-to-br ${game.color} flex items-center justify-center`}>
                  <Gamepad2 className="w-20 h-20 text-white opacity-50" />
                </div>
                <div className="p-6">
                  <div className="text-sm text-purple-400 font-medium mb-2">{game.genre}</div>
                  <h3 className="text-2xl font-bold mb-3">{game.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">
                    Created in 3 days using SparkLabs AI tools
                  </p>
                  <button className="text-sm text-purple-400 font-semibold flex items-center gap-1 hover:text-purple-300">
                    Learn More
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24 md:py-32 bg-slate-900">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">What Creators Say</h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              Join thousands of developers using SparkLabs to bring their ideas to life
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                name: 'Sarah Chen',
                role: 'Indie Game Developer',
                quote: 'SparkLabs cut my development time in half. The AI tools are incredible!'
              },
              {
                name: 'Marcus Johnson',
                role: 'Studio Lead',
                quote: 'We built our entire game in 3 weeks using SparkLabs. It\'s a game-changer.'
              },
              {
                name: 'Emily Rodriguez',
                role: 'Game Designer',
                quote: 'Finally, a tool that lets me focus on creativity instead of tedious work!'
              }
            ].map((testimonial, index) => (
              <div
                key={index}
                className="p-8 bg-slate-800 border border-slate-700 rounded-3xl"
              >
                <div className="flex gap-1 mb-4">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Star key={i} className="w-5 h-5 text-yellow-400 fill-yellow-400" />
                  ))}
                </div>
                <p className="text-lg text-slate-300 mb-6">"{testimonial.quote}"</p>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center font-bold text-lg">
                    {testimonial.name[0]}
                  </div>
                  <div>
                    <div className="font-semibold">{testimonial.name}</div>
                    <div className="text-sm text-slate-500">{testimonial.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-24 md:py-32 bg-slate-950">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">Simple, Transparent Pricing</h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              Choose the perfect plan for your needs
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {[
              {
                name: 'Free',
                price: '$0',
                features: ['Basic AI tools', '3 projects', 'Community access', 'Web export']
              },
              {
                name: 'Pro',
                price: '$29',
                popular: true,
                features: ['All AI tools', 'Unlimited projects', 'Priority support', 'All platforms', 'Asset library']
              },
              {
                name: 'Enterprise',
                price: 'Custom',
                features: ['Custom AI models', 'Dedicated support', 'Team collaboration', 'Custom integrations']
              }
            ].map((plan, index) => (
              <div
                key={index}
                className={`p-8 rounded-3xl border transition-all relative ${
                  plan.popular
                    ? 'bg-gradient-to-b from-purple-900/30 to-slate-900 border-purple-500 shadow-xl'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full text-sm font-semibold">
                    Most Popular
                  </div>
                )}
                <div className="mb-6">
                  <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                  <div className="text-4xl font-black mb-2">{plan.price}</div>
                  <div className="text-slate-500">per month</div>
                </div>
                <ul className="space-y-4 mb-8">
                  {plan.features.map((feature, i) => (
                    <li key={i} className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-purple-400 flex-shrink-0" />
                      <span className="text-slate-300">{feature}</span>
                    </li>
                  ))}
                </ul>
                <button className={`w-full py-4 rounded-2xl font-semibold text-lg transition-all ${
                  plan.popular
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700'
                    : 'bg-slate-800 hover:bg-slate-700 border border-slate-700'
                }`}>
                  Get Started
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 md:py-32 bg-gradient-to-b from-slate-900 to-slate-950 relative overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-gradient-to-br from-purple-900/20 to-pink-900/20 rounded-full blur-3xl" />
        
        <div className="max-w-4xl mx-auto px-6 text-center relative z-10">
          <h2 className="text-4xl md:text-6xl font-black mb-6">
            Start Building Your Dream Game Today
          </h2>
          <p className="text-xl md:text-2xl text-slate-400 mb-10">
            Join thousands of creators using SparkLabs to bring their imagination to life
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button className="px-12 py-5 bg-gradient-to-r from-purple-600 to-pink-600 rounded-2xl font-bold text-xl hover:from-purple-700 hover:to-pink-700 transition-all shadow-2xl hover:shadow-purple-500/40 flex items-center gap-2">
              Get Started for Free
              <ArrowRight className="w-6 h-6" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-950 border-t border-slate-900 py-16">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
                <span className="text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                  SparkLabs
                </span>
              </div>
              <p className="text-slate-500 text-sm">
                AI-powered game development platform for everyone
              </p>
            </div>
            {[
              {
                title: 'Products',
                links: ['Game Studio', 'Asset Generator', 'AI Tools', 'SparkCraft']
              },
              {
                title: 'Company',
                links: ['About', 'Blog', 'Careers', 'Press']
              },
              {
                title: 'Resources',
                links: ['Documentation', 'Tutorials', 'Community', 'Support']
              }
            ].map((column, index) => (
              <div key={index}>
                <h4 className="font-semibold text-slate-300 mb-4">{column.title}</h4>
                <ul className="space-y-3">
                  {column.links.map((link, i) => (
                    <li key={i}>
                      <a href="#" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="border-t border-slate-800 pt-8 text-center text-slate-600 text-sm">
            <p>© 2026 SparkLabs. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
