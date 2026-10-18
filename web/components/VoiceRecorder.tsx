"use client";

import { useRef, useState } from "react";
import { AudioLines, CheckCircle2, Mic, Square, Upload } from "lucide-react";

export function VoiceRecorder({ file, onChange }: { file: File | null; onChange: (file: File | null) => void }) {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState("");
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const stream = useRef<MediaStream | null>(null);

  async function start() {
    setError("");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      const instance = new MediaRecorder(stream.current);
      recorder.current = instance;
      chunks.current = [];
      instance.ondataavailable = (event) => { if (event.data.size) chunks.current.push(event.data); };
      instance.onstop = async () => {
        try {
          const source = new Blob(chunks.current, { type: instance.mimeType || "audio/webm" });
          const context = new AudioContext();
          const decoded = await context.decodeAudioData(await source.arrayBuffer());
          const wav = toWav(decoded);
          await context.close();
          onChange(new File([wav], "dietary-note.wav", { type: "audio/wav" }));
        } catch {
          setError("Couldn’t process this recording. Please try again or upload a WAV audio file.");
        } finally {
          stream.current?.getTracks().forEach((track) => track.stop());
          stream.current = null;
        }
      };
      instance.start();
      setRecording(true);
    } catch {
      setError("Microphone access is unavailable. Allow microphone access or upload a voice note.");
    }
  }

  function stop() {
    if (recorder.current?.state === "recording") recorder.current.stop();
    setRecording(false);
  }

  return <div>
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" onClick={recording ? stop : start} className={`inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-xs font-bold transition ${recording ? "bg-rose-100 text-rose-700" : "bg-[#1c513e] text-white hover:bg-[#123d2e]"}`}>
        {recording ? <><Square size={13} fill="currentColor" /> Stop recording</> : <><Mic size={15} /> Record voice note</>}
      </button>
      <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-[#dce5de] bg-white px-4 py-2.5 text-xs font-bold text-[#456352] hover:bg-[#f6faf6]">
        <Upload size={14} /> Upload audio<input className="sr-only" type="file" accept="audio/*" onChange={(event) => onChange(event.target.files?.[0] || null)} />
      </label>
      {recording && <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-rose-600"><span className="size-2 animate-pulse rounded-full bg-rose-500" /> Recording</span>}
    </div>
    {file && <div className="mt-3 flex items-center gap-2 rounded-xl bg-[#f2f7f2] px-3 py-2 text-xs text-[#4d6c56]"><CheckCircle2 size={15} /> {file.name}<button type="button" className="ml-auto text-[#73857a] underline" onClick={() => onChange(null)}>Remove</button></div>}
    {error && <p className="mt-2 text-xs text-rose-700">{error}</p>}
    <p className="mt-2 flex items-center gap-1.5 text-[10px] leading-4 text-[#8a978d]"><AudioLines size={12} /> Say allergies or conditions clearly. Audio is used for this scan.</p>
  </div>;
}

function toWav(audio: AudioBuffer): Blob {
  const sampleRate = audio.sampleRate;
  const samples = new Float32Array(audio.length);
  for (let channel = 0; channel < audio.numberOfChannels; channel++) {
    const input = audio.getChannelData(channel);
    for (let i = 0; i < input.length; i++) samples[i] += input[i] / audio.numberOfChannels;
  }
  const bytes = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(bytes);
  const write = (offset: number, value: string) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)); };
  write(0, "RIFF"); view.setUint32(4, 36 + samples.length * 2, true); write(8, "WAVE");
  write(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  write(36, "data"); view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return new Blob([bytes], { type: "audio/wav" });
}
