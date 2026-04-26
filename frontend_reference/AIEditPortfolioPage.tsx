import { motion } from 'motion/react';
import { ArrowLeft, Play } from 'lucide-react';
import { Link } from 'react-router';
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { ServiceBookingForm } from '../components/ServiceBookingForm';

interface AIVideo {
  id: number;
  title: string;
  thumbnail: string;
  videoUrl: string;
  category: string;
  duration: string;
  description: string;
}

const aiVideos: AIVideo[] = [
  {
    id: 1,
    title: 'sample 1 ',
    thumbnail: '/images/Ai%20edit.png',
    videoUrl: 'https://www.youtube.com/embed/_KcZp4nIvUY',
    category: 'Captions',
    duration: '5:30',
    description: 'Professional video with AI-generated captions automatically synchronized with audio.'
  },
  {
    id: 2,
    title: 'sample 2',
    thumbnail: '/images/Ai%20edit.png',
    videoUrl: 'https://www.youtube.com/embed/u3OyDaydIpw',
    category: 'Audio',
    duration: '3:45',
    description: 'Crystal clear audio processing using AI voice enhancement technology.'
  },
  {
    id: 3,
    title: 'sample 3',
    thumbnail: '/images/Ai%20edit.png',
    videoUrl: 'https://www.youtube.com/embed/F1yRHMKjJOo',
    category: 'Editing',
    duration: '4:20',
    description: 'AI intelligently identifies and optimizes scene transitions for perfect pacing.'
  },
  {
    id: 4,
    title: 'sample 4',
    thumbnail: '/images/Ai%20edit.png',
    videoUrl: 'https://www.youtube.com/embed/-TKslrccxo4',
    category: 'B-Roll',
    duration: '6:15',
    description: 'AI-generated B-roll seamlessly integrated with original footage.'
  },
  {
    id: 5,
    title: 'sample 5',
    thumbnail: '/images/Ai%20edit.png',
    videoUrl: 'https://www.youtube.com/embed/5y6R7LMUIQ0',
    category: 'Graphics',
    duration: '5:00',
    description: 'AI-created virtual characters and avatars bringing your content to life.'
  },
  {
    id: 6,
    title: 'sample 6',
    thumbnail: '/images/Ai%20edit.png',
    videoUrl: 'https://www.youtube.com/embed/SLqDBXW_QF8',
    category: 'Effects',
    duration: '4:30',
    description: 'Stunning AI-generated visuals and dynamic graphics elevating production quality.'
  },
];

export function AIEditPortfolioPage() {
  const [selectedVideo, setSelectedVideo] = useState<AIVideo | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isBookingModalOpen, setIsBookingModalOpen] = useState(false);

  const handleVideoClick = (video: AIVideo) => {
    setSelectedVideo(video);
    setIsModalOpen(true);
  };

  const handleBooking = () => {
    setIsBookingModalOpen(true);
  };

  const categories = Array.from(new Set(aiVideos.map(v => v.category)));

  return (
    <div className="min-h-screen bg-white">
      {/* Header with back button */}
      <div className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Link
            to="/masterful-editing"
            className="inline-flex items-center gap-2 text-slate-500 hover:text-purple-600 font-bold transition-colors group"
          >
            <ArrowLeft className="w-5 h-5 transform group-hover:-translate-x-1 transition-transform" />
            Back to Editing Services
          </Link>
        </div>
      </div>

      {/* Hero Section */}
      <section className="py-20 bg-[radial-gradient(circle_at_top_right,rgba(147,51,234,0.05)_0%,transparent_50%)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center"
          >
            <h1 className="text-6xl md:text-8xl font-black text-slate-900 mb-8 tracking-tight">
              AI Edit <span className="text-gradient">Portfolio</span>
            </h1>
            <p className="text-xl md:text-2xl text-slate-500 max-w-3xl mx-auto font-light leading-relaxed">
              Next-generation editing powered by AI technology - auto-captions, voice enhancement, smart scene detection, and AI-generated assets.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Category Filter */}
      <section className="py-8 border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-4 overflow-x-auto pb-4 no-scrollbar">
            <button className="px-8 py-3 bg-slate-900 text-white rounded-2xl font-black uppercase tracking-widest text-xs shadow-xl shadow-slate-200">
              All Videos
            </button>
            {categories.map((category) => (
              <button
                key={category}
                className="px-8 py-3 bg-white border border-slate-200 text-slate-600 rounded-2xl font-black uppercase tracking-widest text-xs hover:border-purple-200 hover:bg-slate-50 transition-all font-semibold whitespace-nowrap"
              >
                {category}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Videos Grid */}
      <section className="py-20 pb-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-12">
            {aiVideos.map((video, index) => (
              <motion.div
                key={video.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                onClick={() => handleVideoClick(video)}
                className="group relative bg-white rounded-[40px] overflow-hidden border border-slate-100 hover:border-purple-200 transition-all cursor-pointer shadow-2xl shadow-slate-200/50 hover:shadow-purple-500/10"
              >
                {/* Thumbnail */}
                <div className="relative h-64 overflow-hidden bg-slate-100 p-2">
                  <div className="w-full h-full overflow-hidden rounded-[32px]">
                    <img
                      src={video.thumbnail}
                      alt={video.title}
                      className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-700"
                    />
                  </div>
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-900/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-[32px] m-2" />

                  {/* Play Button */}
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-500 transform scale-50 group-hover:scale-100">
                    <div className="w-20 h-20 bg-white text-purple-600 rounded-full flex items-center justify-center shadow-2xl">
                      <Play className="w-8 h-8 fill-purple-600" />
                    </div>
                  </div>

                  {/* Duration Badge */}
                  <div className="absolute bottom-5 right-5 bg-white/90 backdrop-blur-md px-4 py-1.5 rounded-full text-slate-900 text-sm font-black shadow-lg">
                    {video.duration}
                  </div>

                  {/* Category Badge */}
                  <div className="absolute top-5 left-5 bg-purple-600 px-4 py-1.5 rounded-full text-white text-[10px] font-black uppercase tracking-widest shadow-lg">
                    {video.category}
                  </div>
                </div>

                {/* Content */}
                <div className="p-8">
                  <h3 className="text-2xl font-black text-slate-900 mb-4 group-hover:text-purple-600 transition-colors uppercase tracking-tight">
                    {video.title}
                  </h3>
                  <p className="text-slate-500 text-lg font-light leading-relaxed mb-6">
                    {video.description}
                  </p>

                  {/* Watch Button */}
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full bg-slate-900 text-white px-8 py-4 rounded-2xl font-black uppercase tracking-widest text-xs transition-all shadow-xl shadow-slate-200 group-hover:bg-purple-600"
                  >
                    Watch Now
                  </motion.button>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 bg-slate-900 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(147,51,234,0.2)_0%,transparent_70%)] pointer-events-none" />
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-5xl md:text-7xl font-black text-white mb-8 tracking-tight">
              Embrace the <span className="text-purple-400">Future</span> of Editing
            </h2>
            <p className="text-xl text-slate-400 mb-12 font-light leading-relaxed">
              Leverage cutting-edge AI technology to elevate your content with smart, automated solutions.
            </p>
            <motion.button
              onClick={handleBooking}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-purple-600 text-white px-12 py-5 rounded-2xl text-xl font-black shadow-2xl shadow-purple-500/40 transition-all hover:bg-purple-500 active:scale-95 uppercase tracking-widest text-sm"
            >
              Get Started
            </motion.button>
          </motion.div>
        </div>
      </section>

      {/* Video Player Modal */}
      {selectedVideo && (
        <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
          <DialogContent className="bg-white border border-slate-200 text-slate-900 p-2 overflow-hidden rounded-[40px] shadow-2xl max-w-5xl aspect-video">
            <DialogHeader className="sr-only">
              <DialogTitle>{selectedVideo.title}</DialogTitle>
            </DialogHeader>

            <div className="w-full h-full rounded-[32px] overflow-hidden bg-slate-100 aspect-video">
              <iframe
                width="100%"
                height="100%"
                src={selectedVideo.videoUrl}
                title={selectedVideo.title}
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                className="w-full h-full"
              ></iframe>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
