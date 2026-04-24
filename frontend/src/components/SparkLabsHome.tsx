import React, { useState, useEffect, useRef } from 'react';
import {
  Rocket,
  Zap,
  Star,
  CheckCircle,
  Cpu,
  Image,
  ArrowRight,
  Globe,
  Play,
  Download,
  ChevronRight,
  Terminal,
  Palette,
  Code,
  Brain,
  Sparkles,
  Mail,
  Github,
  Twitter,
  MessageCircle
} from 'lucide-react';

// SparkLabs AI-Native Game Engine Homepage
const SparkLabsHome: React.FC = () => {
  const [scrollY, setScrollY] = useState(0);
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const heroRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleJoinWaitlist = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setIsSubmitted(true);
      setTimeout(() => setIsSubmitted(false), 3000);
      setEmail('');
    }
  };

  const coreFeatures = [
    {
      icon: Sparkles,
      title: 'AI-Native Content Generation',
      description: 'Transform imagination into game assets through neural synthesis. Characters, environments, and narratives emerge from natural language.'
    },
    {
      icon: Brain,
      title: 'AI Gameplay Generation',
      description: 'Every session adapts to the player. AI constructs dynamic mechanics, evolving challenges, and personalized progression paths in real-time.'
    },
    {
      icon: Zap,
      title: 'Real-Time Visual Generation',
      description: 'Neural rendering produces living worlds on demand. Every frame is synthesized instantly, creating infinite visual possibilities without asset constraints.'
    }
  ];

  const engineCapabilities = [
    {
      title: 'Neural Asset Synthesis',
      description: 'Generate textures, sprites, and 3D models from text descriptions',
      icon: Image,
      stat: '10K+ / min'
    },
    {
      title: 'Intelligent Code Assistant',
      description: 'Context-aware scripting that understands game logic patterns',
      icon: Terminal,
      stat: '95% accuracy'
    },
    {
      title: 'Procedural World Builder',
      description: 'Create infinite terrains and levels with AI-driven generation',
      icon: Globe,
      stat: 'Infinite'
    },
    {
      title: 'Adaptive NPC Engine',
      description: 'Characters that learn and evolve based on player behavior',
      icon: Cpu,
      stat: 'Real-time'
    }
  ];

  const testimonials = [
    {
      name: 'Sarah Chen',
      role: 'Indie Developer',
      quote: 'SparkLabs eliminated months of asset creation. I described my vision, and the AI built it in minutes.',
      company: 'Pixel Dreams Studio'
    },
    {
      name: 'Marcus Johnson',
      role: 'Technical Director',
      quote: 'We shipped across 5 platforms in record time. The engine-free approach changed how we think about game development.',
      company: 'Nebula Games'
    },
    {
      name: 'Emily Rodriguez',
      role: 'Creative Lead',
      quote: 'The procedural world builder lets me focus on storytelling while the AI handles technical complexity.',
      company: 'Chronicle Interactive'
    }
  ];

  return (
    <div className="min-h-screen bg-black text-white overflow-x-hidden">
      {/* Ambient Background */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div 
          className="absolute top-0 left-1/2 -translate-x-1/2 w-[2000px] h-[2000px] bg-gradient-to-b from-orange-900/10 via-transparent to-transparent rounded-full blur-3xl"
          style={{ transform: `translate(-50%, ${scrollY * 0.2}px)` }}
        />
        <div 
          className="absolute bottom-0 right-0 w-[1500px] h-[1500px] bg-gradient-to-tl from-red-900/5 via-transparent to-transparent rounded-full blur-3xl"
          style={{ transform: `translate(30%, ${-scrollY * 0.15}px)` }}
        />
        <div 
          className="absolute inset-0 opacity-50"
          style={{
            backgroundImage: 'linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)',
            backgroundSize: '60px 60px'
          }}
        />
      </div>

      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-black/50 backdrop-blur-2xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-gradient-to-br from-orange-500 to-red-600 rounded-full flex items-center justify-center">
                <Zap className="w-4 h-4 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight">
                <span className="bg-gradient-to-r from-orange-400 via-red-500 to-amber-400 bg-clip-text text-transparent">Spark</span>
                <span className="text-white">Labs</span>
              </span>
            </div>
            <div className="hidden lg:flex items-center gap-8">
              {[
                { label: 'About', href: '#about' },
                { label: 'Games', href: '#games' },
                { label: 'Features', href: '#features' },
                { label: 'Community', href: '#community' }
              ].map((item) => (
                <a key={item.label} href={item.href} className="text-white/40 hover:text-white transition-colors font-medium text-sm">
                  {item.label}
                </a>
              ))}
            </div>
            <div className="flex items-center gap-4">
              <button className="hidden sm:block text-white/40 hover:text-white transition-colors font-medium text-sm">
                Sign In
              </button>
              <button className="px-5 py-2 bg-gradient-to-r from-orange-500 to-red-600 rounded-full font-semibold text-sm hover:from-orange-600 hover:to-red-700 transition-all">
                Join Today
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section ref={heroRef} className="relative py-32 lg:py-40 z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div className="text-left">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-full mb-8">
                <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
                <span className="text-orange-300 text-sm font-medium">AI-Native Game Engine Now Available</span>
              </div>

              <h1 className="text-6xl lg:text-8xl font-black mb-8 leading-[0.95] tracking-tight">
                AI-Native
                <br />
                <span className="bg-gradient-to-r from-orange-400 via-red-500 to-amber-400 bg-clip-text text-transparent"
                  style={{ textShadow: '0 0 40px rgba(249,115,22,0.3)' }}>
                  Game Engine
                </span>
              </h1>
              
              <p className="text-xl text-white/40 mb-10 max-w-lg leading-relaxed">
                SparkLabs transforms imagination into interactive experiences. 
                Describe your vision, and watch AI construct entire worlds in real-time.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 mb-12">
                <button className="px-8 py-4 bg-gradient-to-r from-orange-500 to-red-600 rounded-full font-bold text-lg hover:from-orange-600 hover:to-red-700 transition-all shadow-2xl shadow-orange-500/20 flex items-center justify-center gap-3">
                  <Rocket className="w-5 h-5" />
                  Start Creating
                </button>
                <button className="px-8 py-4 bg-white/5 border border-white/10 rounded-full font-bold text-lg hover:bg-white/10 transition-all flex items-center justify-center gap-3">
                  <Play className="w-5 h-5" />
                  Watch Demo
                </button>
              </div>

              {/* Waitlist Form */}
              <div>
                <p className="text-sm text-white/30 mb-3">Join the community of creators on the waitlist</p>
                <form onSubmit={handleJoinWaitlist} className="flex gap-3 max-w-md">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email"
                    className="flex-1 px-5 py-3 bg-white/5 border border-white/10 rounded-full text-sm text-white placeholder-white/30 focus:bg-white/8 focus:border-orange-500/50 focus:outline-none transition-all"
                  />
                  <button
                    type="submit"
                    className="px-6 py-3 bg-white/10 border border-white/20 rounded-full font-semibold text-sm hover:bg-white/20 transition-all whitespace-nowrap"
                  >
                    {isSubmitted ? 'Joined!' : 'Join Waitlist'}
                  </button>
                </form>
              </div>
            </div>

            {/* Interactive Preview */}
            <div className="relative">
              <div className="absolute -inset-8 bg-gradient-to-r from-orange-600/10 to-red-600/10 rounded-[3rem] blur-3xl animate-pulse" style={{ animationDuration: '4s' }} />
              <div className="relative rounded-[2rem] p-2 overflow-hidden" 
                style={{ 
                  background: 'rgba(255,255,255,0.03)', 
                  backdropFilter: 'blur(20px)', 
                  border: '1px solid rgba(255,255,255,0.06)',
                  boxShadow: '0 0 80px rgba(249,115,22,0.15)'
                }}>
                <div className="bg-neutral-950 rounded-[1.5rem] overflow-hidden">
                  <div className="flex items-center gap-3 px-5 py-4 border-b border-white/5">
                    <div className="flex gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500/60" />
                      <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                      <div className="w-3 h-3 rounded-full bg-green-500/60" />
                    </div>
                    <div className="flex-1 text-center text-xs text-white/20 font-mono">SparkLabs Neural Editor</div>
                    <div className="flex items-center gap-2 text-xs text-white/20">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                      Live
                    </div>
                  </div>
                  <div className="aspect-video bg-gradient-to-br from-neutral-900 to-black relative overflow-hidden">
                    {/* Neural Visualization */}
                    <div className="absolute inset-0">
                      <svg className="absolute inset-0 w-full h-full" style={{opacity: 0.3}}>
                        <defs>
                          <linearGradient id="nodeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#f97316" stopOpacity="0.6" />
                            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.2" />
                          </linearGradient>
                        </defs>
                        <line x1="20%" y1="30%" x2="50%" y2="50%" stroke="url(#nodeGrad)" strokeWidth="1" opacity="0.4">
                          <animate attributeName="opacity" values="0.4;0.8;0.4" dur="3s" repeatCount="indefinite" />
                        </line>
                        <line x1="50%" y1="50%" x2="80%" y2="30%" stroke="url(#nodeGrad)" strokeWidth="1" opacity="0.4">
                          <animate attributeName="opacity" values="0.4;0.8;0.4" dur="3s" repeatCount="indefinite" begin="1s" />
                        </line>
                        <line x1="30%" y1="70%" x2="50%" y2="50%" stroke="url(#nodeGrad)" strokeWidth="1" opacity="0.4">
                          <animate attributeName="opacity" values="0.4;0.8;0.4" dur="3s" repeatCount="indefinite" begin="0.5s" />
                        </line>
                        <line x1="50%" y1="50%" x2="70%" y2="70%" stroke="url(#nodeGrad)" strokeWidth="1" opacity="0.4">
                          <animate attributeName="opacity" values="0.4;0.8;0.4" dur="3s" repeatCount="indefinite" begin="1.5s" />
                        </line>
                        <circle cx="20%" cy="30%" r="6" fill="#f97316" opacity="0.8">
                          <animate attributeName="r" values="6;8;6" dur="2s" repeatCount="indefinite" />
                        </circle>
                        <circle cx="50%" cy="50%" r="8" fill="#ef4444" opacity="0.9">
                          <animate attributeName="r" values="8;10;8" dur="2s" repeatCount="indefinite" begin="0.3s" />
                        </circle>
                        <circle cx="80%" cy="30%" r="6" fill="#f97316" opacity="0.8">
                          <animate attributeName="r" values="6;8;6" dur="2s" repeatCount="indefinite" begin="0.6s" />
                        </circle>
                        <circle cx="30%" cy="70%" r="5" fill="#fbbf24" opacity="0.7">
                          <animate attributeName="r" values="5;7;5" dur="2s" repeatCount="indefinite" begin="0.9s" />
                        </circle>
                        <circle cx="70%" cy="70%" r="5" fill="#fbbf24" opacity="0.7">
                          <animate attributeName="r" values="5;7;5" dur="2s" repeatCount="indefinite" begin="1.2s" />
                        </circle>
                      </svg>
                      
                      {/* Floating Data Particles */}
                      <div className="absolute top-1/4 left-1/4 w-2 h-2 bg-orange-400 rounded-full animate-pulse shadow-lg shadow-orange-400/50" />
                      <div className="absolute top-1/3 right-1/4 w-3 h-3 bg-red-400 rounded-full animate-pulse" style={{animationDelay: '0.3s'}} />
                      <div className="absolute bottom-1/3 left-2/3 w-2 h-2 bg-amber-400 rounded-full animate-pulse" style={{animationDelay: '0.6s'}} />
                      
                      {/* Central Processing Core */}
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                        <div className="w-24 h-24 bg-gradient-to-br from-orange-500/20 to-red-600/20 rounded-full blur-2xl animate-pulse" />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <Brain className="w-8 h-8 text-orange-400 animate-pulse" />
                        </div>
                      </div>
                      
                      {/* Code Stream Effect */}
                      <div className="absolute top-4 left-4 font-mono text-xs text-orange-500/30">
                        <div className="animate-pulse">{'>'} neural.generate(world)</div>
                        <div className="animate-pulse" style={{animationDelay: '0.5s'}}>{'>'} asset.create(texture)</div>
                        <div className="animate-pulse" style={{animationDelay: '1s'}}>{'>'} physics.simulate()</div>
                      </div>
                    </div>
                    
                    {/* Bottom Status Bar */}
                    <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-full border border-white/10">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                            <span className="text-xs text-white/50 font-mono">Neural Engine Active</span>
                          </div>
                          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-full border border-white/10">
                            <Zap className="w-3 h-3 text-orange-400" />
                            <span className="text-xs text-white/50 font-mono">60 FPS</span>
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <div className="w-6 h-1 bg-orange-500 rounded-full" />
                          <div className="w-4 h-1 bg-orange-500/60 rounded-full" />
                          <div className="w-3 h-1 bg-orange-500/30 rounded-full" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Features - Three Column Layout */}
      <section id="features" className="py-24 relative z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">AI-Native Creation</h2>
            <p className="text-xl text-white/30 max-w-2xl mx-auto">
              Every aspect of game development powered by neural networks. From concept to playable experience.
            </p>
          </div>

          <div className="grid lg:grid-cols-3 gap-8">
            {coreFeatures.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div key={index} 
                  className="rounded-3xl p-8 transition-all duration-400 hover:-translate-y-2 group"
                  style={{
                    background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)',
                    border: '1px solid rgba(255,255,255,0.06)'
                  }}
                >
                  <div className="w-14 h-14 bg-gradient-to-br from-orange-500/20 to-red-600/20 rounded-2xl flex items-center justify-center mb-6">
                    <Icon className="w-6 h-6 text-orange-400" />
                  </div>
                  <h3 className="text-2xl font-bold mb-4">{feature.title}</h3>
                  <p className="text-white/40 leading-relaxed">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Neural Capabilities */}
      <section id="about" className="py-24 relative z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-20 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-full mb-8">
                <Cpu className="w-4 h-4 text-orange-400" />
                <span className="text-orange-300 text-sm font-medium">Neural Engine</span>
              </div>
              <h2 className="text-5xl lg:text-6xl font-bold mb-8 leading-tight">
                Intelligence Built Into
                <span className="bg-gradient-to-r from-orange-400 via-red-500 to-amber-400 bg-clip-text text-transparent"> Every Pixel</span>
              </h2>
              <p className="text-xl text-white/30 mb-10 leading-relaxed">
                SparkLabs embeds machine learning directly into the rendering pipeline. 
                From texture synthesis to behavioral NPCs, AI accelerates every aspect of game creation.
              </p>
              <button className="px-8 py-4 bg-white/5 border border-white/10 rounded-full font-semibold hover:bg-white/10 transition-all flex items-center gap-3">
                Explore Neural Features
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            <div className="grid gap-4">
              {engineCapabilities.map((capability, index) => {
                const Icon = capability.icon;
                return (
                  <div 
                    key={index} 
                    className="rounded-2xl p-6 transition-all group hover:border-orange-500/20"
                    style={{
                      background: 'rgba(255,255,255,0.03)',
                      backdropFilter: 'blur(20px)',
                      border: '1px solid rgba(255,255,255,0.06)'
                    }}
                  >
                    <div className="flex items-start gap-5">
                      <div className="w-12 h-12 bg-orange-500/10 rounded-xl flex items-center justify-center group-hover:bg-orange-500/20 transition-colors">
                        <Icon className="w-5 h-5 text-orange-400" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-bold text-lg">{capability.title}</h3>
                          <span className="text-xs font-mono text-orange-400 bg-orange-500/10 px-3 py-1 rounded-full">
                            {capability.stat}
                          </span>
                        </div>
                        <p className="text-white/30 text-sm leading-relaxed">{capability.description}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Game Showcase */}
      <section id="games" className="py-24 relative z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">Built With SparkLabs</h2>
            <p className="text-xl text-white/30 max-w-2xl mx-auto">
              Games created by our community using neural-powered development tools
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { title: 'Neon Drift', genre: 'Racing', color: 'from-orange-600 to-red-600', players: '2.4M' },
              { title: 'Void Walker', genre: 'Action RPG', color: 'from-red-600 to-orange-600', players: '1.8M' },
              { title: 'Echoes of AI', genre: 'Puzzle', color: 'from-amber-600 to-orange-600', players: '3.1M' },
              { title: 'Stellar Command', genre: 'Strategy', color: 'from-orange-500 to-red-500', players: '890K' },
              { title: 'Dreamscape', genre: 'Adventure', color: 'from-red-500 to-amber-500', players: '1.2M' },
              { title: 'Quantum Leap', genre: 'Platformer', color: 'from-amber-500 to-orange-600', players: '2.7M' }
            ].map((game, index) => (
              <div key={index} 
                className="rounded-3xl overflow-hidden group transition-all hover:-translate-y-2 hover:shadow-2xl hover:shadow-orange-500/10"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  backdropFilter: 'blur(20px)',
                  border: '1px solid rgba(255,255,255,0.06)'
                }}
              >
                <div className={`h-56 bg-gradient-to-br ${game.color} relative overflow-hidden`}>
                  <div className="absolute inset-0 bg-black/10" />
                  <div className="absolute bottom-4 left-4">
                    <span className="text-xs font-medium bg-black/30 backdrop-blur-md px-4 py-1.5 rounded-full border border-white/10">
                      {game.genre}
                    </span>
                  </div>
                  <div className="absolute top-4 right-4">
                    <span className="text-xs font-medium bg-white/10 backdrop-blur-md px-4 py-1.5 rounded-full border border-white/10">
                      {game.players} players
                    </span>
                  </div>
                </div>
                <div className="p-6">
                  <h3 className="text-xl font-bold mb-2">{game.title}</h3>
                  <p className="text-white/30 text-sm mb-4">Created with AI-generated assets and procedural level design</p>
                  <button className="text-sm text-orange-400 font-semibold flex items-center gap-2 hover:text-orange-300 transition-colors">
                    View Case Study <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="community" className="py-24 relative z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">Trusted by Creators</h2>
            <p className="text-xl text-white/30 max-w-2xl mx-auto">
              Join thousands of developers building the future of gaming
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <div key={index} 
                className="rounded-3xl p-8"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  backdropFilter: 'blur(20px)',
                  border: '1px solid rgba(255,255,255,0.06)'
                }}
              >
                <div className="flex gap-1 mb-6">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Star key={i} className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                  ))}
                </div>
                <p className="text-lg text-white/50 mb-8 leading-relaxed">"{testimonial.quote}"</p>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-red-600 rounded-full flex items-center justify-center font-bold text-lg">
                    {testimonial.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div>
                    <div className="font-semibold text-white">{testimonial.name}</div>
                    <div className="text-sm text-white/30">{testimonial.role}</div>
                    <div className="text-xs text-white/20">{testimonial.company}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Join Today CTA */}
      <section className="py-32 relative z-10 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-orange-950/10 to-transparent" />
        <div className="max-w-4xl mx-auto px-6 text-center relative">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-full mb-8">
            <Sparkles className="w-4 h-4 text-orange-400" />
            <span className="text-orange-300 text-sm font-medium">Limited Early Access</span>
          </div>
          <h2 className="text-5xl lg:text-7xl font-black mb-8 leading-tight">
            Start Building
            <br />
            <span className="bg-gradient-to-r from-orange-400 via-red-500 to-amber-400 bg-clip-text text-transparent">The Future</span>
          </h2>
          <p className="text-xl text-white/30 mb-12 max-w-2xl mx-auto leading-relaxed">
            A growing community of developers uses SparkLabs to craft intelligent, adaptive gaming experiences.
            Early access unlocks exclusive capabilities and dedicated support.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
            <button className="px-10 py-5 bg-gradient-to-r from-orange-500 to-red-600 rounded-full font-bold text-lg hover:from-orange-600 hover:to-red-700 transition-all shadow-2xl shadow-orange-500/20 flex items-center gap-3">
              <Rocket className="w-5 h-5" />
              Join Today
            </button>
            <button className="px-10 py-5 bg-white/5 border border-white/10 rounded-full font-bold text-lg hover:bg-white/10 transition-all flex items-center gap-3">
              <Code className="w-5 h-5" />
              Read Documentation
            </button>
          </div>
          
          {/* Secondary Waitlist */}
          <div className="max-w-md mx-auto">
            <p className="text-sm text-white/20 mb-4">Or join our waitlist for updates</p>
            <form onSubmit={handleJoinWaitlist} className="flex gap-3">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="flex-1 px-5 py-3 bg-white/5 border border-white/10 rounded-full text-sm text-white placeholder-white/20 focus:bg-white/8 focus:border-orange-500/50 focus:outline-none transition-all"
              />
              <button
                type="submit"
                className="px-6 py-3 bg-white/10 border border-white/20 rounded-full font-semibold text-sm hover:bg-white/20 transition-all"
              >
                {isSubmitted ? 'Joined!' : 'Join Waitlist'}
              </button>
            </form>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-20 relative z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-5 gap-12 mb-16">
            <div className="md:col-span-2">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-red-600 rounded-full flex items-center justify-center">
                  <Zap className="w-4 h-4 text-white" />
                </div>
                <span className="text-xl font-bold">
                  <span className="bg-gradient-to-r from-orange-400 via-red-500 to-amber-400 bg-clip-text text-transparent">Spark</span>
                  <span className="text-white">Labs</span>
                </span>
              </div>
              <p className="text-white/20 text-sm max-w-xs leading-relaxed mb-6">
                The AI-native game engine that empowers creators to build intelligent, adaptive gaming experiences.
              </p>
              <div className="flex gap-4">
                {[Twitter, Github, MessageCircle].map((Icon, index) => (
                  <button key={index} className="w-10 h-10 bg-white/5 rounded-full flex items-center justify-center hover:bg-white/10 transition-all">
                    <Icon className="w-4 h-4 text-white/40" />
                  </button>
                ))}
              </div>
            </div>
            {[
              {
                title: 'Product',
                links: ['Features', 'Pricing', 'Changelog', 'Roadmap']
              },
              {
                title: 'Resources',
                links: ['Documentation', 'Tutorials', 'API Reference', 'Community']
              },
              {
                title: 'Company',
                links: ['About', 'Blog', 'Careers', 'Contact']
              }
            ].map((column, index) => (
              <div key={index}>
                <h4 className="font-semibold text-white mb-6">{column.title}</h4>
                <ul className="space-y-4">
                  {column.links.map((link, i) => (
                    <li key={i}>
                      <a href="#" className="text-white/20 hover:text-white/60 text-sm transition-colors">
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="border-t border-white/5 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-white/10 text-sm">© 2026 SparkLabs. All rights reserved.</p>
            <div className="flex items-center gap-8">
              <a href="#" className="text-white/20 hover:text-white/40 text-sm transition-colors">Privacy</a>
              <a href="#" className="text-white/20 hover:text-white/40 text-sm transition-colors">Terms</a>
              <a href="#" className="text-white/20 hover:text-white/40 text-sm transition-colors">Cookies</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default SparkLabsHome;
