
import { motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { Camera, Image as ImageIcon, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router';


interface AiTool {
    id: number;
    title: string;
    icon: React.ReactNode;
    description: string;
    features: string[];
    gradient: string;
    glowColor: string;
    path: string;
    healthEndpoint?: string;
}

function HealthBadge({ url }: { url: string }) {
    const [status, setStatus] = useState<'loading' | 'online' | 'offline'>('loading');

    useEffect(() => {
        fetch(url)
            .then(r => r.json())
            .then(d => setStatus(d.status === 'healthy' ? 'online' : 'offline'))
            .catch(() => setStatus('offline'));
    }, [url]);

    if (status === 'loading') return null;

    return (
        <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border ${
            status === 'online'
                ? 'border-green-300 bg-green-50 text-green-700'
                : 'border-red-300 bg-red-50 text-red-700'
        }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${
                status === 'online' ? 'bg-green-500 animate-pulse' : 'bg-red-500'
            }`} />
            {status === 'online' ? 'Live' : 'Offline'}
        </span>
    );
}

// const aiTools: AiTool[] = [
//     {
//         id: 1,
//         title: 'AI Photo Enhancer',
//         icon: <ImageIcon className="w-8 h-8" />,
//         description: 'Instantly upscale and enhance the quality of your blurry or low-resolution images.',
//         features: ['4K Upscaling', 'Noise Reduction', 'Color Correction', 'Face Enhancement'],
//         gradient: 'from-blue-500 to-indigo-600',
//         glowColor: 'rgba(79, 70, 229, 0.15)',
//         path: 'http://localhost:5000'
//     },
//     {
//         id: 2,
//         title: 'AI Photo Sharing',
//         icon: <Camera className="w-8 h-8" />,
//         description: 'Event code enter karo, selfie upload karo — InsightFace AI tumhari saari photos crowd mein dhundh leta hai instantly.',
//         features: ['Face Recognition (InsightFace)', 'Bulk Batch Upload', 'Event Code System', 'Cosine Similarity Matching'],
//         gradient: 'from-rose-500 to-pink-600',
//         glowColor: 'rgba(236, 72, 153, 0.15)',
//         path: '/ai-photo-sharing',
//         healthEndpoint: 'https://gour-himansh-ai.hf.space/api/health'
//     },
// ];

const aiTools: AiTool[] = [
    {
        id: 2,
        title: 'AI Photo Sharing',
        icon: <Camera className="w-8 h-8" />,
        description: 'Event code enter karo, selfie upload karo — InsightFace AI tumhari saari photos crowd mein dhundh leta hai instantly.',
        features: ['Face Recognition (InsightFace)', 'Bulk Batch Upload', 'Event Code System', 'Cosine Similarity Matching'],
        gradient: 'from-rose-500 to-pink-600',
        glowColor: 'rgba(236, 72, 153, 0.15)',
        path: '/ai-photo-sharing',
        healthEndpoint: 'https://gour-himansh-ai.hf.space/api/health'
    },
];

export function AiToolsSection() {
    const navigate = useNavigate();

    const handleToolClick = (tool: AiTool) => {
        // Internal routes use React Router, external URLs open in new tab
        if (tool.path.startsWith('/')) {
            navigate(tool.path);
        } else {
            window.open(tool.path, '_blank');
        }
    };

    return (
        <section id="ai-tools" className="relative py-16 sm:py-24 bg-deep-space overflow-hidden">
            {/* Background ambient light */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-indigo-200/30 rounded-full blur-[120px]" />
                <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-200/30 rounded-full blur-[120px]" />
            </div>

            <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

                {/* Section Header */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                    className="text-center mb-12 sm:mb-20"
                >
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-indigo-200 bg-indigo-50 mb-6 shadow-sm">
                        <span className="relative flex h-3 w-3">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
                        </span>
                        <span className="text-sm font-medium text-indigo-700 tracking-wide uppercase">Next-Gen AI Capabilities</span>
                    </div>

                    <h2 className="text-3xl sm:text-5xl lg:text-6xl font-black text-slate-900 mb-6 tracking-tight">
                        Supercharge with <br className="hidden sm:block" />
                        <span className="text-gradient">
                            AI Tools Suite
                        </span>
                    </h2>
                    <p className="text-lg sm:text-xl text-slate-500 max-w-2xl mx-auto font-light leading-relaxed">
                        Harness the power of advanced artificial intelligence to elevate your media. Enhance, upscale, and organize with unprecedented speed and precision.
                    </p>
                </motion.div>

                {/* Tools Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 sm:gap-10 perspective-1000">
                    {aiTools.map((tool, index) => (
                        <motion.div
                            key={tool.id}
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.6, delay: index * 0.15 }}
                            whileHover={{ scale: 1.03, translateZ: 40, translateY: -10 }}
                            onClick={() => handleToolClick(tool)}
                            className="group relative flex flex-col h-full rounded-3xl p-8 backdrop-blur-xl border border-slate-200 bg-white/80 transition-all duration-500 cursor-pointer overflow-hidden z-10 hover:shadow-xl"
                            style={{ boxShadow: `0 4px 24px -4px rgba(0,0,0,0.08), 0 0 12px -2px ${tool.glowColor}` }}
                        >
                            {/* Animated Inner Gradients */}
                            <div className={`absolute inset-0 bg-gradient-to-br ${tool.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-700 ease-out`} />

                            <div className="absolute -top-32 -right-32 w-64 h-64 bg-slate-100/50 rounded-full blur-3xl group-hover:bg-slate-200/60 transition-colors duration-700" />
                            <div className={`absolute -bottom-32 -left-32 w-64 h-64 bg-gradient-to-tr ${tool.gradient} opacity-0 group-hover:opacity-10 rounded-full blur-3xl transition-opacity duration-700`} />

                            {/* Icon Container */}
                            <div className="relative z-10 mb-4 inline-flex">
                                <div className={`relative flex items-center justify-center p-4 rounded-2xl bg-gradient-to-br ${tool.gradient} text-white shadow-lg group-hover:shadow-xl transition-shadow duration-500`}>
                                    <motion.div whileHover={{ rotate: 15, scale: 1.1 }} transition={{ type: "spring", stiffness: 300 }}>
                                        {tool.icon}
                                    </motion.div>
                                </div>
                            </div>

                            {/* Live Status Badge */}
                            {tool.healthEndpoint && (
                                <div className="relative z-10 mb-6">
                                    <HealthBadge url={tool.healthEndpoint} />
                                </div>
                            )}

                            {/* Text Content */}
                            <div className="relative z-10 flex-grow">
                                <h3 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-4 tracking-wide group-hover:text-indigo-700 transition-colors duration-300">
                                    {tool.title}
                                </h3>
                                <p className="text-slate-500 text-sm sm:text-base leading-relaxed mb-8 font-light group-hover:text-slate-600 transition-colors duration-300">
                                    {tool.description}
                                </p>

                                {/* Features List */}
                                <ul className="space-y-3 mb-8">
                                    {tool.features.map((feature, idx) => (
                                        <li key={idx} className="flex items-center gap-3 text-sm text-slate-600 font-medium">
                                            <div className={`w-1.5 h-1.5 rounded-full bg-gradient-to-r ${tool.gradient}`} />
                                            {feature}
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {/* Action Button */}
                            <div className="relative z-10 mt-auto pt-6 border-t border-slate-200">
                                <motion.div
                                    className="flex items-center text-sm font-semibold text-slate-800 gap-2 group-hover:gap-4 transition-all duration-300"
                                >
                                    <span className="tracking-wider uppercase">Launch Tool</span>
                                    <div className={`p-1.5 rounded-full bg-gradient-to-r ${tool.gradient} shadow-md`}>
                                        <ArrowRight className="w-4 h-4 text-white" />
                                    </div>
                                </motion.div>
                            </div>

                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
