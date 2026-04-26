import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from './ui/dialog';
import { supabase } from '../../lib/supabase';

interface ServiceBookingFormProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  selectedService: string;
}


export function ServiceBookingForm({
  isOpen,
  onOpenChange,
  selectedService,
}: ServiceBookingFormProps) {
  const shootTypes = [
    'Wedding Shoot',
    'Insta & YouTube Video Shoot',
    'Commercial Shoot',
    'Corporate Event Shoot',
    'Marketing Shoot',
    'Religious Shoot',
    'Political Shoot',
    'Cinematic Shoot',
  ];

  const serviceOptions = [
    'Vlog Edit',
    'Documentary Edit',
    'Reel Edit',
    'AI Edit',
    'Custom Edit',
    'Wedding Edit',
    'Professional Shoot',
  ];

  const [formData, setFormData] = useState({
    // Personal Information
    name: '',
    email: '',
    whatsappNumber: '',
    location: '',

    // Project Details
    editingOption: selectedService || '',
    projectTitle: '',
    description: '',

    // Budget & Timeline
    budget: '',
    timeline: '',

    // References
    referenceVideoLink: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Update form when selectedService changes
  useEffect(() => {
    if (isOpen && selectedService) {
      setFormData((prev) => ({
        ...prev,
        editingOption: selectedService,
      }));
    }
  }, [isOpen, selectedService]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError(null);

    const commonData = {
      name: formData.name,
      email: formData.email,
      whatsapp_number: formData.whatsappNumber,
      location: formData.location,
      budget: formData.budget,
      timeline: formData.timeline,
      reference_video_link: formData.referenceVideoLink || null,
    };

    try {
      if (isShootBooking) {
        const { error } = await supabase.from('shoot_bookings').insert([{
          ...commonData,
          shoot_type: formData.editingOption,
          event_details: formData.description,
        }]);
        if (error) throw error;
      } else {
        const { error } = await supabase.from('bookings').insert([{
          ...commonData,
          service_type: formData.editingOption,
          project_title: formData.projectTitle,
          description: formData.description,
        }]);
        if (error) throw error;
      }

      // Reset form on success
      setFormData({
        name: '',
        email: '',
        whatsappNumber: '',
        location: '',
        editingOption: selectedService || '',
        projectTitle: '',
        description: '',
        budget: '',
        timeline: '',
        referenceVideoLink: '',
      });
      onOpenChange(false);
      alert(`✅ ${isShootBooking ? 'Shoot' : 'Service'} booking saved successfully!`);
    } catch (error: any) {
      console.error('Supabase booking error:', error);
      setSubmitError(error.message || 'Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };



  const isShootBooking = shootTypes.includes(formData.editingOption);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="bg-white/95 border border-slate-200 text-slate-900 max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl shadow-indigo-500/10 backdrop-blur-2xl">
        <DialogHeader>
          <DialogTitle className="text-3xl font-black text-slate-900 tracking-tight">
            Book Your <span className="text-gradient">Service</span>
          </DialogTitle>
          <DialogDescription className="text-slate-500 font-light">
            Fill in the form below to request your service and we'll get back to you soon.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6 pr-4">
          {/* Section 1: Personal Information */}
          <div className="space-y-4 pb-4 border-b border-slate-100">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <span className="text-indigo-500">👤</span> Personal Information
            </h3>

            {/* Name Field */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-700">
                Full Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="Enter your name"
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
                required
              />
            </div>

            {/* Email Field */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-700">
                Email Address <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="you@example.com"
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
                required
              />
            </div>

            {/* WhatsApp Number Field */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-700">
                WhatsApp Number <span className="text-red-500">*</span>
              </label>
              <input
                type="tel"
                name="whatsappNumber"
                value={formData.whatsappNumber}
                onChange={handleInputChange}
                placeholder="+91 98765 43210 or 10 digit number"
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
                required
              />
            </div>

            {/* Location Field */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-700">
                Location <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="location"
                value={formData.location}
                onChange={handleInputChange}
                placeholder="Select or type your location"
                list="locationList"
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
                required
              />
              <datalist id="locationList">
                <option value="sehore" />
                <option value="bhopal" />
                <option value="Indore" />
                <option value="Gwalior" />
                <option value="Ujjain" />
                <option value="Jabalpur" />
                <option value="Mumbai" />
                <option value="Delhi" />
                <option value="Bangalore" />
                <option value="Hyderabad" />
                <option value="Chennai" />
                <option value="Kolkata" />
                <option value="Pune" />
                <option value="Ahmedabad" />
                <option value="Jaipur" />
                <option value="Lucknow" />

              </datalist>
            </div>
          </div>

          {/* Section 2: Project Details */}
          <div className="space-y-4 pb-4 border-b border-slate-100">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <span className="text-purple-500">🎬</span> {isShootBooking ? 'Shoot Details' : 'Project Details'}
            </h3>

            {/* Service/Shoot Selection */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-700">
                {isShootBooking ? 'Select Shoot' : 'Editing Service'} <span className="text-red-500">*</span>
              </label>
              <select
                name="editingOption"
                value={formData.editingOption}
                onChange={handleInputChange}
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all [&>option]:bg-white"
                required
              >
                <option value="">Select a {isShootBooking ? 'shoot type' : 'service'}</option>
                {isShootBooking ? (
                  shootTypes.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))
                ) : (
                  serviceOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* Project Title - Only for editing services */}
            {!isShootBooking && (
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-slate-700">
                  Project Title
                </label>
                <input
                  type="text"
                  name="projectTitle"
                  value={formData.projectTitle}
                  onChange={handleInputChange}
                  placeholder="e.g., Summer Travel Vlog Series"
                  className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
                />
              </div>
            )}

            {/* Description - Only for editing services */}
            {!isShootBooking && (
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-slate-700">
                  Project Description
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  placeholder="Describe your project, requirements, and specific needs..."
                  rows={3}
                  className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all resize-none"
                />
              </div>
            )}

            {/* For shoot bookings, show event details instead */}
            {isShootBooking && (
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-slate-700">
                  Event/Project Details
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  placeholder="Tell us more about your shoot - location, date, special requirements..."
                  rows={3}
                  className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all resize-none"
                />
              </div>
            )}
          </div>



          {/* Section 4: Budget & Timeline */}
          <div className="space-y-4 pb-4 border-b border-slate-100">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <span className="text-emerald-500">💰</span> Budget & Timeline
            </h3>

            {/* Budget */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-700">
                Budget Range <span className="text-red-500">*</span>
              </label>
              <select
                name="budget"
                value={formData.budget}
                onChange={handleInputChange}
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all [&>option]:bg-white"
                required
              >
                <option value="">Select budget</option>
                <option value="₹0-500">₹0-500</option>
                <option value="₹500-1000">₹500-1000</option>
                <option value="₹1000-2500">₹1000-2500</option>
                <option value="₹2500-5000">₹2500-5000</option>
                <option value="₹5000+">₹5000+</option>
              </select>
            </div>

            {/* Timeline */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-700">
                Required Timeline <span className="text-red-500">*</span>
              </label>
              <select
                name="timeline"
                value={formData.timeline}
                onChange={handleInputChange}
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all [&>option]:bg-white"
                required
              >
                <option value="">Select timeline</option>
                <option value="Urgent (24-48 hours)">Urgent (24-48 hours)</option>
                <option value="ASAP (3-7 days)">ASAP (3-7 days)</option>
                <option value="1-2 weeks">1-2 weeks</option>
                <option value="2-4 weeks">2-4 weeks</option>
                <option value="Flexible">Flexible</option>
              </select>
            </div>
          </div>

          {/* Section 5: References & Links */}
          <div className="space-y-4 pb-4">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <span className="text-orange-500">🔗</span> References & Links
            </h3>

            {/* Reference Video Link */}
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-700">
                Reference Video Link
              </label>
              <input
                type="url"
                name="referenceVideoLink"
                value={formData.referenceVideoLink}
                onChange={handleInputChange}
                placeholder="https://youtu.be/... or https://drive.google.com/..."
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all"
              />
            </div>

          </div>

          {/* Submit Button */}
          {submitError && (
            <p className="text-red-500 text-sm font-medium text-center">{submitError}</p>
          )}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-slate-900 hover:bg-indigo-600 text-white px-8 py-5 rounded-2xl font-black uppercase tracking-widest text-xs transition-all shadow-xl shadow-slate-200 mt-6 active:scale-95 disabled:opacity-60"
          >
            {isSubmitting ? 'Saving...' : 'Save Booking'}
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
