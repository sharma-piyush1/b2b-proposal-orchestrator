"use client";

import { useState, useRef, useEffect } from "react";
import { Play, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Sphere, MeshDistortMaterial } from "@react-three/drei";
import * as THREE from "three";

// WebGL Reactive Component
function AICore({ isSpeaking }: { isSpeaking: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = state.clock.elapsedTime * 0.2;
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.3;
      
      // Scale pulse effect tied to speech state
      const scale = isSpeaking ? 1 + Math.sin(state.clock.elapsedTime * 15) * 0.05 : 1;
      meshRef.current.scale.set(scale, scale, scale);
    }
  });

  return (
    <Sphere ref={meshRef} args={[1.8, 64, 64]}>
      <MeshDistortMaterial
        color={isSpeaking ? "#10b981" : "#3b82f6"} // Green when speaking, Blue when idle
        attach="material"
        distort={isSpeaking ? 0.6 : 0.2}
        speed={isSpeaking ? 5 : 1}
        roughness={0.2}
        metalness={0.8}
      />
    </Sphere>
  );
}

export default function ProposalDashboard() {
  const [rfpText, setRfpText] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "paused_for_review" | "completed">("idle");
  const [proposalData, setProposalData] = useState<any>(null);
  const [threadId] = useState(`thread_${Math.random().toString(36).substring(7)}`);
  const [isSpeaking, setIsSpeaking] = useState(false);
  
  // SSR Guard for WebGL
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Dynamic API Routing Setup
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const generateProposal = async () => {
    setStatus("loading");
    try {
      const response = await fetch(`${API_URL}/generate-proposal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rfp_text: rfpText, thread_id: threadId }),
      });
      const result = await response.json();
      setProposalData(result.data);
      setStatus(result.status);
    } catch (error) {
      console.error("API Error:", error);
      setStatus("idle");
    }
  };

  const handlePricingApproval = async (isApproved: boolean) => {
    setStatus("loading");
    try {
      const response = await fetch(`${API_URL}/approve-pricing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, is_approved: isApproved }),
      });
      const result = await response.json();
      setProposalData(result.data);
      setStatus(result.status);
      
      if (result.status === "completed" && result.data.drafted_sections?.executive_summary) {
        speakText(result.data.drafted_sections.executive_summary.content);
      }
    } catch (error) {
      console.error("API Error:", error);
      setStatus("idle");
    }
  };

  const speakText = (text: string) => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1;
      
      // Event listeners to trigger WebGL state changes
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      window.speechSynthesis.speak(utterance);
    } else {
      console.warn("Web Speech API not supported in this browser.");
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 p-8 font-sans text-gray-900">
      <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Left Column: Input and Controls */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h1 className="text-2xl font-bold mb-4">Enterprise RFP Orchestrator</h1>
          <p className="text-gray-600 mb-4 text-sm">Submit technical requirements to initialize the multi-agent workflow.</p>
          
          <textarea
            className="w-full h-40 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none mb-4"
            placeholder="Paste RFP requirements here..."
            value={rfpText}
            onChange={(e) => setRfpText(e.target.value)}
            disabled={status !== "idle"}
          />
          
          {status === "idle" && (
            <button
              onClick={generateProposal}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg transition-colors"
            >
              Initialize Agent Workflow
            </button>
          )}

          {status === "loading" && (
            <div className="flex items-center justify-center py-3 text-blue-600">
              <Loader2 className="animate-spin mr-2" /> Processing Graph State...
            </div>
          )}

          {status === "paused_for_review" && proposalData && (
            <div className="mt-6 bg-amber-50 border border-amber-200 p-4 rounded-lg">
              <h3 className="text-amber-800 font-bold mb-2">⚠️ Human Approval Required</h3>
              <p className="text-sm text-amber-900 mb-4">
                The pricing agent has calculated the financial model. Review the costs before authorizing document generation.
              </p>
              <div className="flex space-x-4">
                <button
                  onClick={() => handlePricingApproval(true)}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-2 rounded-md flex items-center justify-center"
                >
                  <CheckCircle className="w-4 h-4 mr-2" /> Approve
                </button>
                <button
                  onClick={() => handlePricingApproval(false)}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold py-2 rounded-md flex items-center justify-center"
                >
                  <XCircle className="w-4 h-4 mr-2" /> Reject
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Avatar and Output State */}
        <div className="space-y-6">
          {/* WebGL Canvas */}
          <div className="bg-slate-900 rounded-xl h-64 shadow-inner relative overflow-hidden cursor-move">
            {isMounted && (
              <Canvas className="w-full h-full">
                <ambientLight intensity={0.5} />
                <directionalLight position={[2, 5, 2]} intensity={1} />
                <AICore isSpeaking={isSpeaking} />
                <OrbitControls enableZoom={false} />
              </Canvas>
            )}
          </div>

          {/* State Inspector */}
          {proposalData && (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 h-[calc(100%-17rem)] overflow-y-auto">
              <h2 className="text-lg font-bold border-b pb-2 mb-4">Workflow State</h2>
              
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Architecture</h4>
                <p className="text-sm">Infra: {proposalData.extracted_requirements?.infrastructure}</p>
                <p className="text-sm">Latency: {proposalData.extracted_requirements?.latency_sla}</p>
              </div>

              {proposalData.financial_pricing && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Pricing Model</h4>
                  <p className="text-sm">License: ${proposalData.financial_pricing.software_license_cost}</p>
                  <p className="text-sm">Implementation: ${proposalData.financial_pricing.implementation_fee}</p>
                </div>
              )}

              {status === "completed" && proposalData.drafted_sections?.executive_summary && (
                <div className="mt-4 p-4 bg-blue-50 border border-blue-100 rounded-lg">
                  <h4 className="font-bold text-blue-900 mb-2">Final Proposal</h4>
                  <p className="text-blue-800 whitespace-pre-wrap">{proposalData.drafted_sections.executive_summary.content}</p>
                </div>
              )}
            </div>
          )}
        </div>

      </div>
    </main>
  );
}