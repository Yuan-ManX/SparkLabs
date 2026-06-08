"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/engine";

interface AudioStats {
  sample_rate: number;
  master_volume: number;
  generated_count: number;
  total_samples: number;
  stored_samples: number;
  oscillators: number;
  filters: number;
  effects: number;
}

interface OscillatorInfo {
  id: string;
  waveform: string;
  frequency: number;
  amplitude: number;
  detune_cents: number;
  enabled: boolean;
}

interface AudioSampleInfo {
  id: string;
  sample_rate: number;
  channels: number;
  bit_depth: number;
  duration_ms: number;
  sample_count: number;
  duration_seconds: number;
}

interface ScaleNote {
  name: string;
  frequency: number;
  interval: number;
}

type TabId = "stats" | "synthesis" | "music" | "samples";

export default function AudioSynthesisPanel() {
  const [activeTab, setActiveTab] = useState<TabId>("stats");
  const [stats, setStats] = useState<AudioStats | null>(null);
  const [oscillators, setOscillators] = useState<OscillatorInfo[]>([]);
  const [samples, setSamples] = useState<AudioSampleInfo[]>([]);
  const [scaleNotes, setScaleNotes] = useState<ScaleNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  // Synthesis form
  const [effectType, setEffectType] = useState("laser");
  const [frequency, setFrequency] = useState("440");
  const [duration, setDuration] = useState("500");
  const [amplitude, setAmplitude] = useState("0.5");

  // Music form
  const [scaleType, setScaleType] = useState("major");
  const [rootNote, setRootNote] = useState("C4");
  const [chordType, setChordType] = useState("major");
  const [noteCount, setNoteCount] = useState("8");
  const [bpm, setBpm] = useState("120");

  // Oscillator form
  const [oscWaveform, setOscWaveform] = useState("sine");
  const [oscFreq, setOscFreq] = useState("440");
  const [oscAmp, setOscAmp] = useState("0.5");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/audio-synthesis/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchOscillators = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/audio-synthesis/oscillators`);
      const data = await res.json();
      if (data.oscillators) setOscillators(data.oscillators);
    } catch {}
  }, []);

  const fetchSamples = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/audio-synthesis/samples`);
      const data = await res.json();
      if (data.samples) setSamples(data.samples);
    } catch {}
  }, []);

  const fetchScale = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/audio-synthesis/scale/${scaleType}?root_note=${rootNote}`);
      const data = await res.json();
      if (data.notes) setScaleNotes(data.notes);
    } catch {}
  }, [scaleType, rootNote]);

  useEffect(() => {
    fetchStats();
    fetchOscillators();
    fetchSamples();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchOscillators, fetchSamples]);

  useEffect(() => {
    if (activeTab === "music") fetchScale();
  }, [activeTab, fetchScale]);

  const showMessage = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(""), 3000);
  };

  const handleSynthesizeEffect = async () => {
    try {
      const res = await fetch(`${API_BASE}/audio-synthesis/sfx/${effectType}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          frequency: parseFloat(frequency),
          duration_ms: parseFloat(duration),
          amplitude: parseFloat(amplitude),
          start_freq: parseFloat(frequency),
          end_freq: parseFloat(frequency) * 0.5,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Synthesized: ${effectType} (${data.duration_ms}ms)`);
        fetchSamples();
      }
    } catch {
      showMessage("Failed to synthesize effect");
    }
  };

  const handleGenerateNoise = async () => {
    try {
      const res = await fetch(`${API_BASE}/audio-synthesis/noise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          color: "white",
          duration_ms: parseFloat(duration),
          amplitude: parseFloat(amplitude),
        }),
      });
      const data = await res.json();
      if (!data.error) {
        showMessage(`Noise generated: ${data.duration_ms}ms`);
        fetchSamples();
      }
    } catch {
      showMessage("Failed to generate noise");
    }
  };

  const handleGenerateChord = async () => {
    try {
      const res = await fetch(`${API_BASE}/audio-synthesis/chord`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          root_note: rootNote,
          chord_type: chordType,
          duration_ms: parseFloat(duration),
          amplitude: parseFloat(amplitude),
        }),
      });
      const data = await res.json();
      if (!data.error) {
        showMessage(`Chord: ${rootNote} ${chordType}`);
        fetchSamples();
      }
    } catch {
      showMessage("Failed to generate chord");
    }
  };

  const handleGenerateMelody = async () => {
    try {
      const res = await fetch(`${API_BASE}/audio-synthesis/melody`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scale_type: scaleType,
          root_note: rootNote,
          note_count: parseInt(noteCount),
          amplitude: parseFloat(amplitude),
        }),
      });
      const data = await res.json();
      if (!data.error) {
        showMessage(`Melody: ${scaleType} ${rootNote}`);
        fetchSamples();
      }
    } catch {
      showMessage("Failed to generate melody");
    }
  };

  const handleGenerateRhythm = async () => {
    try {
      const res = await fetch(`${API_BASE}/audio-synthesis/rhythm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bpm: parseFloat(bpm),
          beats: 8,
          amplitude: parseFloat(amplitude),
        }),
      });
      const data = await res.json();
      if (!data.error) {
        showMessage(`Rhythm: ${bpm} BPM`);
        fetchSamples();
      }
    } catch {
      showMessage("Failed to generate rhythm");
    }
  };

  const handleAddOscillator = async () => {
    try {
      const res = await fetch(`${API_BASE}/audio-synthesis/oscillators`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          waveform: oscWaveform,
          frequency: parseFloat(oscFreq),
          amplitude: parseFloat(oscAmp),
        }),
      });
      const data = await res.json();
      if (!data.error) {
        showMessage("Oscillator created");
        fetchOscillators();
      }
    } catch {
      showMessage("Failed to create oscillator");
    }
  };

  const handleRemoveOscillator = async (id: string) => {
    try {
      await fetch(`${API_BASE}/audio-synthesis/oscillators/${id}`, { method: "DELETE" });
      fetchOscillators();
    } catch {}
  };

  const TABS: { id: TabId; label: string }[] = [
    { id: "stats", label: "Statistics" },
    { id: "synthesis", label: "Synthesis" },
    { id: "music", label: "Music" },
    { id: "samples", label: "Samples" },
  ];

  const EFFECT_TYPES = ["laser", "explosion", "collect", "jump", "hit", "powerup", "ambient"];
  const WAVEFORMS = ["sine", "square", "sawtooth", "triangle", "pulse", "noise"];
  const SCALE_TYPES = ["major", "minor", "pentatonic_major", "pentatonic_minor", "chromatic", "blues", "dorian", "phrygian", "lydian", "mixolydian"];
  const CHORD_TYPES = ["major", "minor", "diminished", "augmented", "sus2", "sus4", "major7", "minor7", "dominant7"];

  if (loading) {
    return (
      <div style={{ padding: 24, color: "#a0a0b0" }}>
        Loading Audio Synthesis...
      </div>
    );
  }

  return (
    <div style={{ padding: 24, color: "#e0e0e0" }}>
      <h2 style={{ margin: "0 0 8px 0", fontSize: 20, color: "#fff" }}>
        Audio Synthesis
      </h2>
      <p style={{ margin: "0 0 16px 0", fontSize: 12, color: "#888" }}>
        Procedural audio generation, sound effects, and musical composition
      </p>

      {/* Tab Navigation */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "1px solid #333" }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "8px 16px",
              background: "none",
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid #6366f1" : "2px solid transparent",
              color: activeTab === tab.id ? "#6366f1" : "#888",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: activeTab === tab.id ? 600 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div style={{
          padding: "8px 12px",
          background: "#1a1a2e",
          border: "1px solid #6366f1",
          borderRadius: 6,
          marginBottom: 12,
          fontSize: 12,
          color: "#a5b4fc",
        }}>
          {message}
        </div>
      )}

      {/* Statistics Tab */}
      {activeTab === "stats" && (
        <div>
          {stats ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
              <StatCard label="Sample Rate" value={`${stats.sample_rate} Hz`} />
              <StatCard label="Master Volume" value={`${(stats.master_volume * 100).toFixed(0)}%`} />
              <StatCard label="Generated" value={String(stats.generated_count)} />
              <StatCard label="Total Samples" value={stats.total_samples.toLocaleString()} />
              <StatCard label="Stored" value={String(stats.stored_samples)} />
              <StatCard label="Oscillators" value={String(stats.oscillators)} />
              <StatCard label="Filters" value={String(stats.filters)} />
              <StatCard label="Effects" value={String(stats.effects)} />
            </div>
          ) : (
            <p style={{ color: "#888" }}>No statistics available</p>
          )}

          {/* Oscillators */}
          <h3 style={{ margin: "20px 0 12px", fontSize: 14, color: "#ccc" }}>Oscillators</h3>
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            <select value={oscWaveform} onChange={(e) => setOscWaveform(e.target.value)}
              style={selectStyle}>
              {WAVEFORMS.map((w) => (
                <option key={w} value={w}>{w}</option>
              ))}
            </select>
            <input type="number" value={oscFreq} onChange={(e) => setOscFreq(e.target.value)}
              placeholder="Freq" style={inputStyle} />
            <input type="number" value={oscAmp} onChange={(e) => setOscAmp(e.target.value)}
              placeholder="Amp" style={inputStyle} step="0.1" min="0" max="1" />
            <button onClick={handleAddOscillator} style={buttonStyle}>Add</button>
          </div>
          {oscillators.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {oscillators.map((osc) => (
                <div key={osc.id} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "8px 12px", background: "#1a1a2e", borderRadius: 6, fontSize: 12,
                }}>
                  <span>
                    <span style={{ color: "#6366f1" }}>{osc.waveform}</span>
                    {" "}{osc.frequency}Hz / {osc.amplitude}
                  </span>
                  <button onClick={() => handleRemoveOscillator(osc.id)}
                    style={{ ...buttonStyle, padding: "2px 8px", fontSize: 11, background: "#ef4444" }}>
                    Remove
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "#666", fontSize: 12 }}>No oscillators</p>
          )}
        </div>
      )}

      {/* Synthesis Tab */}
      {activeTab === "synthesis" && (
        <div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <label style={{ fontSize: 12, color: "#888" }}>Effect:</label>
              <select value={effectType} onChange={(e) => setEffectType(e.target.value)}
                style={selectStyle}>
                {EFFECT_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <label style={{ fontSize: 12, color: "#888" }}>Freq:</label>
              <input type="number" value={frequency} onChange={(e) => setFrequency(e.target.value)}
                style={{ ...inputStyle, width: 80 }} />
              <label style={{ fontSize: 12, color: "#888" }}>Dur:</label>
              <input type="number" value={duration} onChange={(e) => setDuration(e.target.value)}
                style={{ ...inputStyle, width: 80 }} />
              <label style={{ fontSize: 12, color: "#888" }}>Amp:</label>
              <input type="number" value={amplitude} onChange={(e) => setAmplitude(e.target.value)}
                style={{ ...inputStyle, width: 80 }} step="0.1" min="0" max="1" />
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button onClick={handleSynthesizeEffect} style={buttonStyle}>
                Synthesize {effectType}
              </button>
              <button onClick={handleGenerateNoise} style={{ ...buttonStyle, background: "#7c3aed" }}>
                Generate Noise
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Music Tab */}
      {activeTab === "music" && (
        <div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <label style={{ fontSize: 12, color: "#888" }}>Scale:</label>
              <select value={scaleType} onChange={(e) => setScaleType(e.target.value)}
                style={selectStyle}>
                {SCALE_TYPES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <label style={{ fontSize: 12, color: "#888" }}>Root:</label>
              <select value={rootNote} onChange={(e) => setRootNote(e.target.value)}
                style={selectStyle}>
                {["C4","D4","E4","F4","G4","A4","B4"].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              <label style={{ fontSize: 12, color: "#888" }}>Chord:</label>
              <select value={chordType} onChange={(e) => setChordType(e.target.value)}
                style={selectStyle}>
                {CHORD_TYPES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <label style={{ fontSize: 12, color: "#888" }}>Notes:</label>
              <input type="number" value={noteCount} onChange={(e) => setNoteCount(e.target.value)}
                style={{ ...inputStyle, width: 60 }} />
              <label style={{ fontSize: 12, color: "#888" }}>BPM:</label>
              <input type="number" value={bpm} onChange={(e) => setBpm(e.target.value)}
                style={{ ...inputStyle, width: 60 }} />
              <label style={{ fontSize: 12, color: "#888" }}>Amp:</label>
              <input type="number" value={amplitude} onChange={(e) => setAmplitude(e.target.value)}
                style={{ ...inputStyle, width: 80 }} step="0.1" min="0" max="1" />
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button onClick={handleGenerateChord} style={{ ...buttonStyle, background: "#8b5cf6" }}>
                Generate Chord
              </button>
              <button onClick={handleGenerateMelody} style={{ ...buttonStyle, background: "#a855f7" }}>
                Generate Melody
              </button>
              <button onClick={handleGenerateRhythm} style={{ ...buttonStyle, background: "#c084fc" }}>
                Generate Rhythm
              </button>
            </div>

            {/* Scale Notes */}
            {scaleNotes.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <h4 style={{ fontSize: 13, color: "#aaa", margin: "0 0 8px" }}>
                  {scaleType} scale - {rootNote}
                </h4>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {scaleNotes.map((note, idx) => (
                    <div key={idx} style={{
                      padding: "4px 10px",
                      background: "#1a1a2e",
                      border: "1px solid #333",
                      borderRadius: 4,
                      fontSize: 11,
                      color: "#c4b5fd",
                    }}>
                      {note.name} ({note.frequency.toFixed(1)}Hz)
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Samples Tab */}
      {activeTab === "samples" && (
        <div>
          {samples.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {samples.map((s) => (
                <div key={s.id} style={{
                  padding: "10px 14px",
                  background: "#1a1a2e",
                  borderRadius: 6,
                  fontSize: 12,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}>
                  <div>
                    <span style={{ color: "#6366f1", fontFamily: "monospace" }}>{s.id}</span>
                    <span style={{ color: "#888", marginLeft: 12 }}>
                      {s.sample_rate}Hz / {s.channels}ch / {s.bit_depth}bit
                    </span>
                  </div>
                  <div style={{ color: "#888" }}>
                    {s.sample_count.toLocaleString()} samples / {s.duration_ms}ms ({s.duration_seconds.toFixed(2)}s)
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "#666", fontSize: 12 }}>No samples generated yet</p>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      padding: "14px 16px",
      background: "#1a1a2e",
      borderRadius: 8,
      border: "1px solid #2a2a3e",
    }}>
      <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: "#6366f1" }}>{value}</div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "6px 10px",
  background: "#0f0f23",
  border: "1px solid #333",
  borderRadius: 4,
  color: "#e0e0e0",
  fontSize: 12,
  width: 100,
};

const selectStyle: React.CSSProperties = {
  padding: "6px 10px",
  background: "#0f0f23",
  border: "1px solid #333",
  borderRadius: 4,
  color: "#e0e0e0",
  fontSize: 12,
};

const buttonStyle: React.CSSProperties = {
  padding: "6px 14px",
  background: "#6366f1",
  color: "#fff",
  border: "none",
  borderRadius: 4,
  cursor: "pointer",
  fontSize: 12,
  fontWeight: 500,
};