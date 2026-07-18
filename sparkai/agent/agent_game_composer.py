"""
SparkLabs Agent - Game Composer

An AI agent that generates procedural background music for games using
the Web Audio API. The composer analyzes the game's genre and mood,
then algorithmically composes a chord progression, melody, bassline,
and drum pattern that matches the game's emotional tone.

This is a core AI-native capability: traditional engines require manual
music composition, but an AI-native engine generates adaptive music
automatically based on the game's design parameters.

Architecture:
  GameComposer (singleton)
    |-- MoodAnalyzer     -> detects mood from game genre and HTML
    |-- ScaleGenerator   -> selects musical scale based on mood
    |-- ChordProgression -> generates chord progressions
    |-- MelodyGenerator  -> composes melody lines
    |-- BasslineBuilder  -> creates bass patterns
    |-- DrumPattern      -> generates rhythmic patterns
    |-- JsCompiler       -> converts composition to Web Audio API JS

Mood Mapping:
  - platformer: energetic, major pentatonic, 140 BPM
  - puzzle: calm, major pentatonic, 90 BPM
  - shooter: intense, minor scale, 160 BPM
  - rpg: epic, dorian mode, 110 BPM
  - racing: driving, mixolydian, 150 BPM
  - narrative: ambient, lydian, 80 BPM
  - survival: tense, phrygian, 130 BPM
  - strategy: thoughtful, dorian, 95 BPM
  - sandbox: playful, major, 120 BPM
  - default: balanced, major, 110 BPM
"""

from __future__ import annotations

import json
import random
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Musical Constants
# ---------------------------------------------------------------------------

# Note frequencies (C4 = 261.63 Hz, using equal temperament)
NOTE_FREQS: Dict[str, float] = {
    "C": 261.63, "C#": 277.18, "D": 293.66, "D#": 311.13,
    "E": 329.63, "F": 349.23, "F#": 369.99, "G": 392.00,
    "G#": 415.30, "A": 440.00, "A#": 466.16, "B": 493.88,
}

# Scale intervals (semitones from root)
SCALES: Dict[str, List[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
}

# Chord qualities (semitone offsets from root)
CHORD_TYPES: Dict[str, List[int]] = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "dom7": [0, 4, 7, 10],
    "sus4": [0, 5, 7],
}

# Genre to mood mapping
GENRE_MOOD: Dict[str, Dict[str, Any]] = {
    "platformer": {"mood": "energetic", "scale": "pentatonic_major", "tempo": 140, "root": "C", "progression": [0, 4, 5, 3]},
    "puzzle": {"mood": "calm", "scale": "pentatonic_major", "tempo": 90, "root": "D", "progression": [0, 3, 4, 1]},
    "shooter": {"mood": "intense", "scale": "minor", "tempo": 160, "root": "A", "progression": [0, 5, 3, 4]},
    "rpg": {"mood": "epic", "scale": "dorian", "tempo": 110, "root": "D", "progression": [0, 3, 4, 0]},
    "racing": {"mood": "driving", "scale": "mixolydian", "tempo": 150, "root": "E", "progression": [0, 4, 5, 3]},
    "narrative": {"mood": "ambient", "scale": "lydian", "tempo": 80, "root": "F", "progression": [0, 1, 4, 3]},
    "music": {"mood": "rhythmic", "scale": "major", "tempo": 128, "root": "C", "progression": [0, 4, 5, 3]},
    "survival": {"mood": "tense", "scale": "phrygian", "tempo": 130, "root": "E", "progression": [0, 1, 0, 6]},
    "strategy": {"mood": "thoughtful", "scale": "dorian", "tempo": 95, "root": "A", "progression": [0, 3, 4, 1]},
    "sandbox": {"mood": "playful", "scale": "major", "tempo": 120, "root": "G", "progression": [0, 4, 5, 3]},
    "exploration": {"mood": "wondrous", "scale": "lydian", "tempo": 100, "root": "C", "progression": [0, 1, 3, 4]},
    "default": {"mood": "balanced", "scale": "major", "tempo": 110, "root": "C", "progression": [0, 4, 5, 3]},
}


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class Note:
    """A single musical note."""
    pitch: str  # e.g. "C4", "E#4"
    frequency: float
    duration: float  # in beats
    velocity: float = 0.6  # 0.0 to 1.0
    start_beat: float = 0.0


@dataclass
class Track:
    """A musical track (melody, bass, drums, etc.)."""
    name: str
    notes: List[Note] = field(default_factory=list)
    instrument: str = "oscillator"  # oscillator, square, sawtooth, noise
    volume: float = 0.5


@dataclass
class Composition:
    """A complete musical composition."""
    tempo: int  # BPM
    mood: str
    scale_name: str
    root_note: str
    key: str
    tracks: List[Track] = field(default_factory=list)
    total_beats: float = 16.0  # 4 bars of 4/4
    progression: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tempo": self.tempo,
            "mood": self.mood,
            "scale_name": self.scale_name,
            "root_note": self.root_note,
            "key": self.key,
            "total_beats": self.total_beats,
            "progression": self.progression,
            "tracks": [
                {
                    "name": t.name,
                    "instrument": t.instrument,
                    "volume": t.volume,
                    "note_count": len(t.notes),
                }
                for t in self.tracks
            ],
        }


@dataclass
class CompositionResult:
    """Result of a composition generation."""
    session_id: str
    success: bool
    composition: Optional[Composition]
    js_code: str
    genre: str
    mood: str
    duration_s: float
    error: Optional[str] = None

    def to_dict(self, include_js: bool = True) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "session_id": self.session_id,
            "success": self.success,
            "composition": self.composition.to_dict() if self.composition else None,
            "genre": self.genre,
            "mood": self.mood,
            "duration_s": round(self.duration_s, 3),
            "error": self.error,
        }
        if include_js:
            result["js_code"] = self.js_code
        return result


# ---------------------------------------------------------------------------
# Game Composer Singleton
# ---------------------------------------------------------------------------


class GameComposer:
    """AI agent that generates procedural background music for games.

    Analyzes the game's genre and mood, then composes a complete musical
    piece (chord progression, melody, bassline, drums) and compiles it
    into JavaScript that plays using the Web Audio API.
    """

    _instance: Optional["GameComposer"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "GameComposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._initialized = False
                    cls._instance = obj
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GameComposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls()
        return cls._instance  # type: ignore[return-value]

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._inner_lock: threading.RLock = threading.RLock()
            self._history: List[CompositionResult] = []
            self._total_compositions: int = 0
            self._initialized = True

    # -- Public API --------------------------------------------------------

    def compose(
        self,
        genre: str = "",
        html: str = "",
        mood_override: str = "",
        bars: int = 4,
    ) -> CompositionResult:
        """Compose procedural background music for a game.

        Args:
            genre: Game genre (platformer, puzzle, shooter, etc.)
            html: Optional game HTML for genre detection
            mood_override: Optional mood override
            bars: Number of bars to compose (default 4)

        Returns:
            CompositionResult with the JS code to play the music.
        """
        import time
        import uuid
        start = time.time()
        session_id = f"comp_{uuid.uuid4().hex[:12]}"

        try:
            # Detect genre from HTML if not provided
            if not genre and html:
                genre = self._detect_genre(html)
            genre = genre.lower().strip()
            mood_config = GENRE_MOOD.get(genre, GENRE_MOOD["default"])

            if mood_override:
                mood_config = {**mood_config, "mood": mood_override}

            # Generate composition
            composition = self._generate_composition(mood_config, bars)

            # Compile to JavaScript
            js_code = self._compile_to_js(composition)

            result = CompositionResult(
                session_id=session_id,
                success=True,
                composition=composition,
                js_code=js_code,
                genre=genre,
                mood=mood_config["mood"],
                duration_s=time.time() - start,
            )

            with self._inner_lock:
                self._history.append(result)
                if len(self._history) > 50:
                    self._history.pop(0)
                self._total_compositions += 1

            return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            return CompositionResult(
                session_id=session_id,
                success=False,
                composition=None,
                js_code="",
                genre=genre,
                mood="",
                duration_s=time.time() - start,
                error=str(e),
            )

    def compose_and_inject(self, html: str, genre: str = "") -> Tuple[str, CompositionResult]:
        """Compose music and inject it into game HTML.

        Returns the modified HTML and the composition result.
        """
        result = self.compose(genre=genre, html=html)
        if not result.success or not result.js_code:
            return html, result

        js_block = f"\n<!-- SparkLabs Composer: {result.mood} BGM -->\n{result.js_code}\n"
        if "</body>" in html:
            healed_html = html.replace("</body>", js_block + "</body>", 1)
        else:
            healed_html = html + js_block
        return healed_html, result

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._inner_lock:
            return [r.to_dict(include_js=False) for r in self._history[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._inner_lock:
            return {
                "initialized": self._initialized,
                "total_compositions": self._total_compositions,
                "supported_genres": list(GENRE_MOOD.keys()),
                "supported_scales": list(SCALES.keys()),
            }

    # -- Genre Detection ---------------------------------------------------

    def _detect_genre(self, html: str) -> str:
        """Detect game genre from HTML content."""
        html_lower = html.lower()
        genre_keywords: Dict[str, List[str]] = {
            "platformer": ["platformer", "jump", "gravity", "platform"],
            "puzzle": ["puzzle", "match", "tile", "swap"],
            "shooter": ["shooter", "bullet", "shoot", "laser"],
            "rpg": ["rpg", "quest", "inventory", "character"],
            "racing": ["racing", "car", "track", "speed", "lap"],
            "narrative": ["narrative", "story", "dialogue", "choice"],
            "music": ["music", "rhythm", "beat", "tempo"],
            "survival": ["survival", "wave", "horde", "resource"],
            "strategy": ["strategy", "tower", "build", "deploy"],
            "sandbox": ["sandbox", "creative", "build", "free"],
        }
        scores: Dict[str, int] = {}
        for genre, keywords in genre_keywords.items():
            score = sum(1 for kw in keywords if kw in html_lower)
            if score > 0:
                scores[genre] = score
        if scores:
            return max(scores, key=scores.get)
        return "default"

    # -- Composition Generation --------------------------------------------

    def _generate_composition(self, mood_config: Dict[str, Any], bars: int) -> Composition:
        """Generate a complete musical composition."""
        root = mood_config["root"]
        scale_name = mood_config["scale"]
        tempo = mood_config["tempo"]
        mood = mood_config["mood"]
        progression_degrees = mood_config["progression"]

        scale_intervals = SCALES[scale_name]
        root_freq = NOTE_FREQS[root]

        # Generate scale frequencies (2 octaves)
        scale_freqs: List[float] = []
        for octave in range(2):
            for interval in scale_intervals:
                freq = root_freq * (2 ** (interval / 12.0)) * (2 ** octave)
                scale_freqs.append(freq)

        total_beats = bars * 4.0

        # Generate tracks
        melody_track = self._generate_melody(scale_freqs, progression_degrees, total_beats, mood)
        bass_track = self._generate_bassline(root_freq, scale_intervals, progression_degrees, total_beats, mood)
        chord_track = self._generate_chords(root_freq, scale_intervals, progression_degrees, total_beats)
        drum_track = self._generate_drums(total_beats, tempo, mood)

        return Composition(
            tempo=tempo,
            mood=mood,
            scale_name=scale_name,
            root_note=root,
            key=f"{root} {scale_name}",
            tracks=[melody_track, bass_track, chord_track, drum_track],
            total_beats=total_beats,
            progression=progression_degrees,
        )

    def _generate_melody(
        self,
        scale_freqs: List[float],
        progression: List[int],
        total_beats: float,
        mood: str,
    ) -> Track:
        """Generate a melody track."""
        notes: List[Note] = []
        beat = 0.0
        # Use a seed for reproducibility within a session
        rng = random.Random(42)

        while beat < total_beats:
            # Determine which chord degree is active
            chord_idx = int((beat / total_beats) * len(progression)) % len(progression)
            degree = progression[chord_idx]

            # Choose a note from the scale, preferring chord tones
            chord_tone_offset = degree * 2 % len(scale_freqs)
            if rng.random() < 0.6:
                # Chord tone
                idx = chord_tone_offset + rng.choice([0, 2, 4])
            else:
                # Passing tone
                idx = rng.randint(0, len(scale_freqs) - 1)
            idx = idx % len(scale_freqs)
            freq = scale_freqs[idx]

            # Duration: mostly quarter/eighth notes, occasional long notes
            if mood in ("calm", "ambient", "thoughtful"):
                duration = rng.choice([2.0, 2.0, 1.0, 1.0, 0.5])
            elif mood in ("intense", "driving", "energetic"):
                duration = rng.choice([0.5, 0.5, 0.25, 1.0, 0.5])
            else:
                duration = rng.choice([1.0, 1.0, 0.5, 0.5, 2.0])

            velocity = rng.uniform(0.4, 0.7)
            notes.append(Note(
                pitch=f"freq_{freq:.2f}",
                frequency=freq,
                duration=duration,
                velocity=velocity,
                start_beat=beat,
            ))
            beat += duration

        return Track(name="melody", notes=notes, instrument="triangle", volume=0.4)

    def _generate_bassline(
        self,
        root_freq: float,
        scale_intervals: List[int],
        progression: List[int],
        total_beats: float,
        mood: str,
    ) -> Track:
        """Generate a bassline track."""
        notes: List[Note] = []
        beats_per_chord = total_beats / len(progression)

        for i, degree in enumerate(progression):
            chord_start = i * beats_per_chord
            # Bass plays root note one octave below
            interval = scale_intervals[degree % len(scale_intervals)]
            bass_freq = root_freq * (2 ** (interval / 12.0)) * 0.5  # one octave down

            if mood in ("calm", "ambient"):
                # Long sustained notes
                notes.append(Note(
                    pitch=f"bass_{bass_freq:.2f}",
                    frequency=bass_freq,
                    duration=beats_per_chord,
                    velocity=0.5,
                    start_beat=chord_start,
                ))
            else:
                # Rhythmic bass: root on beat 1 and 3
                notes.append(Note(
                    pitch=f"bass_{bass_freq:.2f}",
                    frequency=bass_freq,
                    duration=1.5,
                    velocity=0.6,
                    start_beat=chord_start,
                ))
                notes.append(Note(
                    pitch=f"bass_{bass_freq:.2f}",
                    frequency=bass_freq,
                    duration=1.5,
                    velocity=0.5,
                    start_beat=chord_start + 2.0,
                ))

        return Track(name="bass", notes=notes, instrument="sine", volume=0.5)

    def _generate_chords(
        self,
        root_freq: float,
        scale_intervals: List[int],
        progression: List[int],
        total_beats: float,
    ) -> Track:
        """Generate a chord/pad track."""
        notes: List[Note] = []
        beats_per_chord = total_beats / len(progression)

        for i, degree in enumerate(progression):
            chord_start = i * beats_per_chord
            # Build a triad from the scale degree
            root_idx = degree % len(scale_intervals)
            third_idx = (degree + 2) % len(scale_intervals)
            fifth_idx = (degree + 4) % len(scale_intervals)

            for idx in [root_idx, third_idx, fifth_idx]:
                interval = scale_intervals[idx]
                freq = root_freq * (2 ** (interval / 12.0))
                notes.append(Note(
                    pitch=f"chord_{freq:.2f}",
                    frequency=freq,
                    duration=beats_per_chord * 0.9,
                    velocity=0.25,
                    start_beat=chord_start,
                ))

        return Track(name="chords", notes=notes, instrument="sine", volume=0.2)

    def _generate_drums(self, total_beats: float, tempo: int, mood: str) -> Track:
        """Generate a drum track using noise bursts."""
        notes: List[Note] = []
        # Drum patterns: kick on 1 and 3, snare on 2 and 4, hi-hat on eighth notes
        for beat in range(int(total_beats)):
            # Kick
            if beat % 2 == 0:
                notes.append(Note(
                    pitch="kick",
                    frequency=60.0,
                    duration=0.3,
                    velocity=0.7,
                    start_beat=float(beat),
                ))
            # Snare
            if beat % 2 == 1:
                notes.append(Note(
                    pitch="snare",
                    frequency=200.0,
                    duration=0.2,
                    velocity=0.5,
                    start_beat=float(beat),
                ))
            # Hi-hat (eighth notes)
            if mood not in ("calm", "ambient", "thoughtful"):
                notes.append(Note(
                    pitch="hihat",
                    frequency=8000.0,
                    duration=0.1,
                    velocity=0.2,
                    start_beat=float(beat) + 0.5,
                ))

        return Track(name="drums", notes=notes, instrument="noise", volume=0.3)

    # -- JavaScript Compilation --------------------------------------------

    def _compile_to_js(self, composition: Composition) -> str:
        """Compile a composition into Web Audio API JavaScript."""
        # Build note data for each track
        tracks_js: List[str] = []
        for track in composition.tracks:
            notes_data: List[str] = []
            for note in track.notes:
                notes_data.append(
                    f"{{f:{note.frequency:.2f},s:{note.start_beat:.2f},"
                    f"d:{note.duration:.2f},v:{note.velocity:.2f},"
                    f"p:\"{note.pitch}\"}}"
                )
            tracks_js.append(
                f'{{name:"{track.name}",inst:"{track.instrument}",'
                f'vol:{track.volume},notes:[{",".join(notes_data)}]}}'
            )

        tracks_json = f"[{','.join(tracks_js)}]"

        # Use __PLACEHOLDER__ to avoid f-string brace conflicts
        js_template = """<script>
(function() {
  var SL_BGM_CTX = null;
  var SL_BGM_GAIN = null;
  var SL_BGM_PLAYING = false;
  var SL_BGM_TIMEOUTS = [];
  var SL_BGM_TRACKS = __TRACKS_JSON__;
  var SL_BGM_TEMPO = __TEMPO__;
  var SL_BGM_BEAT_DUR = 60.0 / SL_BGM_TEMPO;

  function slGetCtx() {
    if (!SL_BGM_CTX) {
      try { SL_BGM_CTX = new (window.AudioContext || window.webkitAudioContext)(); }
      catch(e) { return null; }
    }
    return SL_BGM_CTX;
  }

  function slPlayNote(freq, startBeat, duration, velocity, instrument, masterGain) {
    var ctx = slGetCtx();
    if (!ctx) return;
    var startTime = ctx.currentTime + (startBeat * SL_BGM_BEAT_DUR);
    var durSec = duration * SL_BGM_BEAT_DUR;

    if (instrument === 'noise') {
      // Drum: use noise burst
      var bufferSize = ctx.sampleRate * durSec;
      var buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      var data = buffer.getChannelData(0);
      for (var i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * (1 - i / bufferSize);
      }
      var src = ctx.createBufferSource();
      src.buffer = buffer;
      var filt = ctx.createBiquadFilter();
      filt.type = 'bandpass';
      filt.frequency.value = freq;
      filt.Q.value = 2;
      var g = ctx.createGain();
      g.gain.value = velocity * masterGain;
      src.connect(filt);
      filt.connect(g);
      g.connect(ctx.destination);
      src.start(startTime);
      src.stop(startTime + durSec);
    } else {
      // Tonal: use oscillator
      var osc = ctx.createOscillator();
      var g = ctx.createGain();
      var oscType = 'sine';
      if (instrument === 'triangle') oscType = 'triangle';
      else if (instrument === 'square') oscType = 'square';
      else if (instrument === 'sawtooth') oscType = 'sawtooth';
      osc.type = oscType;
      osc.frequency.value = freq;
      g.gain.setValueAtTime(0, startTime);
      g.gain.linearRampToValueAtTime(velocity * masterGain, startTime + 0.02);
      g.gain.exponentialRampToValueAtTime(0.001, startTime + durSec);
      osc.connect(g);
      g.connect(ctx.destination);
      osc.start(startTime);
      osc.stop(startTime + durSec + 0.05);
    }
  }

  window.slStartBGM = function() {
    if (SL_BGM_PLAYING) return;
    var ctx = slGetCtx();
    if (!ctx) return;
    if (ctx.state === 'suspended') ctx.resume();
    SL_BGM_PLAYING = true;
    var totalDur = __TOTAL_BEATS__ * SL_BGM_BEAT_DUR * 1000;

    function scheduleLoop() {
      if (!SL_BGM_PLAYING) return;
      for (var t = 0; t < SL_BGM_TRACKS.length; t++) {
        var track = SL_BGM_TRACKS[t];
        for (var n = 0; n < track.notes.length; n++) {
          var note = track.notes[n];
          slPlayNote(note.f, note.s, note.d, note.v, track.inst, track.vol);
        }
      }
      // Schedule next loop
      var to = setTimeout(scheduleLoop, totalDur);
      SL_BGM_TIMEOUTS.push(to);
    }
    scheduleLoop();
  };

  window.slStopBGM = function() {
    SL_BGM_PLAYING = false;
    for (var i = 0; i < SL_BGM_TIMEOUTS.length; i++) {
      clearTimeout(SL_BGM_TIMEOUTS[i]);
    }
    SL_BGM_TIMEOUTS = [];
  };

  window.slToggleBGM = function() {
    if (SL_BGM_PLAYING) window.slStopBGM();
    else window.slStartBGM();
  };

  // Auto-start after user interaction (browsers require user gesture)
  var _slBgmStarted = false;
  function _slTryStart() {
    if (!_slBgmStarted) {
      _slBgmStarted = true;
      window.slStartBGM();
    }
  }
  document.addEventListener('click', _slTryStart, { once: true });
  document.addEventListener('keydown', _slTryStart, { once: true });
  document.addEventListener('touchstart', _slTryStart, { once: true });

  // Add a mute button
  var _slBtn = document.createElement('button');
  _slBtn.innerHTML = '\\u266B';
  _slBtn.style.cssText = 'position:fixed;top:8px;right:44px;z-index:9997;background:rgba(20,20,20,0.8);color:#f97316;border:1px solid #333;border-radius:6px;width:32px;height:32px;font-size:16px;cursor:pointer;';
  _slBtn.onclick = function(e) { e.stopPropagation(); window.slToggleBGM(); };
  document.body.appendChild(_slBtn);
})();
</script>"""

        js = js_template.replace("__TRACKS_JSON__", tracks_json)
        js = js.replace("__TEMPO__", str(composition.tempo))
        js = js.replace("__TOTAL_BEATS__", str(composition.total_beats))
        return js


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_game_composer() -> GameComposer:
    """Return the singleton GameComposer instance."""
    return GameComposer.get_instance()
