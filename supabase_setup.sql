-- SQL Script to Set Up Tables for GlobalAuthGate
-- Run this in your Supabase SQL Editor

-- Table for "Login as Customer" (Leads)
CREATE TABLE IF NOT EXISTS public.leads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL
);

-- Enable Row Level Security (RLS) for leads
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;

-- Allow anonymous inserts to the leads table
DROP POLICY IF EXISTS "Allow public inserts on leads" ON public.leads;
CREATE POLICY "Allow public inserts on leads"
ON public.leads
FOR INSERT 
TO public
WITH CHECK (true);


-- Table for "Login for Work" (Work Applications)
CREATE TABLE IF NOT EXISTS public.work_applications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    full_name TEXT NOT NULL,
    whatsapp TEXT NOT NULL,
    location TEXT NOT NULL,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    skills TEXT NOT NULL,
    equipment TEXT NOT NULL,
    portfolio TEXT NOT NULL
);

-- Enable Row Level Security (RLS) for work_applications
ALTER TABLE public.work_applications ENABLE ROW LEVEL SECURITY;

-- Allow anonymous inserts to the work_applications table
DROP POLICY IF EXISTS "Allow public inserts on work_applications" ON public.work_applications;
CREATE POLICY "Allow public inserts on work_applications"
ON public.work_applications
FOR INSERT 
TO public
WITH CHECK (true);


-- Table for Contact Us Queries
CREATE TABLE IF NOT EXISTS public.querries (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL
);

-- Enable Row Level Security (RLS) for querries
ALTER TABLE public.querries ENABLE ROW LEVEL SECURITY;

-- Allow anonymous inserts to the querries table
DROP POLICY IF EXISTS "Allow public inserts on querries" ON public.querries;
CREATE POLICY "Allow public inserts on querries"
ON public.querries
FOR INSERT 
TO public
WITH CHECK (true);

