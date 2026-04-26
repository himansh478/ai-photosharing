import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router";

export function AiPhotoSharingPage() {
    const navigate = useNavigate();

    return (
        <div className="fixed inset-0 w-full h-full bg-white z-[100] flex flex-col">
            {/* Overlay Navigation Header */}
            <div className="absolute top-4 left-4 z-10">
                <button 
                    onClick={() => navigate('/')}
                    className="flex items-center gap-2 px-6 py-3 bg-white/90 backdrop-blur-md border border-slate-200 rounded-full text-slate-900 hover:text-indigo-600 hover:bg-white hover:border-indigo-200 transition-all shadow-xl shadow-slate-200 group"
                >
                    <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
                    <span className="font-bold tracking-tight">Back to Home</span>
                </button>
            </div>
            
            {/* Azure App Service — Production Deployment */}
            <iframe 
                src="https://ai.cwaya.me"
                className="w-full h-full border-none shadow-2xl"
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="AI Photo Sharing App"
                allow="camera; microphone; clipboard-write; self"
            ></iframe>
        </div>
    );
}
