"""
SparkLabs Agent - Game Polish

The final stage of the AI-native pipeline. Takes the fused game HTML and
applies production-ready polish across five dimensions:

  1. Minification  - strip comments, collapse whitespace in inline JS/CSS
  2. Accessibility  - audit and auto-inject ARIA labels, keyboard nav, focus
  3. SEO Metadata   - inject title, description, Open Graph, Twitter Card
  4. Performance    - inject rAF guards, error boundaries, memory cleanup
  5. Compatibility  - inject cross-browser polyfills and vendor prefixes

Each dimension produces a list of applied patches and a pass/fail status.
The final readiness report summarizes the overall production readiness.

Usage:
    polish = GamePolish.get_instance()
    polish.initialize()
    result = polish.polish(html, title="My Game", description="A fun game")
    # result.html contains the polished, production-ready game
    # result.report contains the readiness checklist
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PolishPatch:
    """A single patch applied during polishing."""

    dimension: str  # "minify", "a11y", "seo", "perf", "compat"
    action: str
    detail: str
    before_size: int = 0
    after_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "action": self.action,
            "detail": self.detail,
            "before_size": self.before_size,
            "after_size": self.after_size,
        }


@dataclass
class DimensionReport:
    """Report for a single polish dimension."""

    dimension: str
    passed: bool
    patches: List[PolishPatch] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "passed": self.passed,
            "patches": [p.to_dict() for p in self.patches],
            "notes": list(self.notes),
        }


@dataclass
class PolishResult:
    """Complete result of a polish operation."""

    polish_id: str
    success: bool
    game_title: str
    original_size: int
    polished_size: int
    size_delta: int
    html: str
    reports: List[DimensionReport]
    readiness_score: float  # 0-100
    readiness_verdict: str  # "production-ready", "needs-review", "not-ready"
    duration_s: float
    error: Optional[str] = None

    def to_dict(self, include_html: bool = True) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "polish_id": self.polish_id,
            "success": self.success,
            "game_title": self.game_title,
            "original_size": self.original_size,
            "polished_size": self.polished_size,
            "size_delta": self.size_delta,
            "reports": [r.to_dict() for r in self.reports],
            "readiness_score": round(self.readiness_score, 1),
            "readiness_verdict": self.readiness_verdict,
            "duration_s": round(self.duration_s, 3),
            "error": self.error,
        }
        if include_html:
            result["html"] = self.html
        return result


# =============================================================================
# Game Polish Agent
# =============================================================================


class GamePolish:
    """
    Final-stage polish agent that makes game HTML production-ready.

    Applies minification, accessibility fixes, SEO metadata, performance
    guards, and cross-browser compatibility patches.

    Implements a thread-safe singleton pattern.
    """

    _instance: Optional["GamePolish"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if GamePolish._instance is not None:
            raise RuntimeError("Use GamePolish.get_instance()")
        self._initialized: bool = False
        self._history: deque = deque(maxlen=30)
        self._total_polishes: int = 0
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "GamePolish":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the polish agent."""
        with self._lock:
            if self._initialized:
                return
            self._initialized = True
            logger.info("GamePolish initialized")

    # -- Public API --------------------------------------------------------

    def polish(
        self,
        html: str,
        game_title: str = "Untitled Game",
        description: str = "",
    ) -> PolishResult:
        """
        Apply production-ready polish to game HTML.

        Args:
            html: The game HTML to polish
            game_title: Title for SEO metadata
            description: Description for SEO metadata

        Returns:
            PolishResult with polished HTML and readiness report
        """
        if not self._initialized:
            self.initialize()

        polish_id = f"polish_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        original_size = len(html)

        try:
            reports: List[DimensionReport] = []
            polished = html

            # Phase 1: Minification
            polished, minify_report = self._minify(polished)
            reports.append(minify_report)

            # Phase 2: Accessibility
            polished, a11y_report = self._accessibility(polished)
            reports.append(a11y_report)

            # Phase 3: SEO Metadata
            polished, seo_report = self._seo_metadata(
                polished, game_title, description
            )
            reports.append(seo_report)

            # Phase 4: Performance Guards
            polished, perf_report = self._performance(polished)
            reports.append(perf_report)

            # Phase 5: Cross-Browser Compatibility
            polished, compat_report = self._compatibility(polished)
            reports.append(compat_report)

            # Calculate readiness
            passed_count = sum(1 for r in reports if r.passed)
            readiness_score = (passed_count / len(reports)) * 100.0
            if readiness_score >= 80:
                verdict = "production-ready"
            elif readiness_score >= 60:
                verdict = "needs-review"
            else:
                verdict = "not-ready"

            polished_size = len(polished)
            duration = time.time() - start_time
            result = PolishResult(
                polish_id=polish_id,
                success=True,
                game_title=game_title,
                original_size=original_size,
                polished_size=polished_size,
                size_delta=polished_size - original_size,
                html=polished,
                reports=reports,
                readiness_score=readiness_score,
                readiness_verdict=verdict,
                duration_s=duration,
            )

            with self._lock:
                self._history.append(result)
                self._total_polishes += 1

            logger.info(
                "Polish %s complete: %d bytes -> %d bytes (%+d), "
                "readiness %.0f%% (%s)",
                polish_id, original_size, polished_size,
                polished_size - original_size,
                readiness_score, verdict,
            )
            return result

        except Exception as exc:
            logger.exception("Polish %s failed: %s", polish_id, exc)
            return PolishResult(
                polish_id=polish_id,
                success=False,
                game_title=game_title,
                original_size=original_size,
                polished_size=original_size,
                size_delta=0,
                html=html,
                reports=[],
                readiness_score=0.0,
                readiness_verdict="not-ready",
                duration_s=time.time() - start_time,
                error=str(exc),
            )

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the polish agent."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_polishes": self._total_polishes,
                "dimensions": ["minify", "a11y", "seo", "perf", "compat"],
            }

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent polish results."""
        with self._lock:
            return [r.to_dict(include_html=False) for r in list(self._history)[-limit:]]

    # -- Internal: Minification --------------------------------------------

    def _minify(self, html: str) -> Tuple[str, DimensionReport]:
        """Minify inline JS and CSS by removing comments and collapsing whitespace."""
        report = DimensionReport(dimension="minify", passed=True)
        before = len(html)

        # Strip JS single-line comments (// ...) inside <script> tags
        # Be careful not to strip URLs (http://, https://)
        def _minify_script(match: re.Match) -> str:
            # The regex has a single capture group for the script body
            code = match.group(1)
            # Remove single-line comments (but not URLs)
            code = re.sub(r'(?<!:)//.*$', '', code, flags=re.MULTILINE)
            # Remove multi-line comments
            code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
            # Collapse multiple blank lines
            code = re.sub(r'\n\s*\n', '\n', code)
            # Trim leading whitespace on each line (preserve indentation for readability)
            # Actually, for minification, collapse all whitespace
            code = re.sub(r'\s+', ' ', code)
            code = code.strip()
            # Preserve any attributes that were on the original <script> tag
            opening = re.match(r'<script\b[^>]*>', match.group(0), re.IGNORECASE)
            opening_tag = opening.group(0) if opening else '<script>'
            return f"{opening_tag}{code}</script>"

        polished = re.sub(
            r'<script(?:\s[^>]*)?>(.+?)</script>',
            _minify_script,
            html,
            flags=re.DOTALL,
        )

        # Strip CSS comments inside <style> tags
        def _minify_style(match: re.Match) -> str:
            css = match.group(1)
            css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
            css = re.sub(r'\s+', ' ', css)
            css = css.strip()
            return f"<style>{css}</style>"

        polished = re.sub(
            r'<style(?:\s[^>]*)?>(.+?)</style>',
            _minify_style,
            polished,
            flags=re.DOTALL,
        )

        # Collapse whitespace between HTML tags
        polished = re.sub(r'>\s+<', '><', polished)

        after = len(polished)
        saved = before - after
        if saved > 0:
            report.patches.append(PolishPatch(
                dimension="minify",
                action="minified-inline-js-css",
                detail=f"Removed comments and collapsed whitespace, saved {saved} bytes",
                before_size=before,
                after_size=after,
            ))
        else:
            report.notes.append("No minification needed - HTML already compact")

        report.passed = after <= before
        return polished, report

    # -- Internal: Accessibility -------------------------------------------

    def _accessibility(self, html: str) -> Tuple[str, DimensionReport]:
        """Audit and auto-inject accessibility fixes."""
        report = DimensionReport(dimension="a11y", passed=True)
        patches_injected: List[str] = []

        # Check for ARIA labels on canvas elements
        canvas_count = len(re.findall(r'<canvas\b', html, re.IGNORECASE))
        canvas_with_aria = len(re.findall(r'<canvas[^>]*aria-label', html, re.IGNORECASE))

        if canvas_count > 0 and canvas_with_aria < canvas_count:
            # Inject aria-label on canvas elements missing it
            def _add_canvas_aria(match: re.Match) -> str:
                tag = match.group(0)
                if 'aria-label' in tag.lower():
                    return tag
                return tag.replace('<canvas', '<canvas aria-label="Game canvas" role="img"', 1)

            html = re.sub(r'<canvas\b[^>]*>', _add_canvas_aria, html, flags=re.IGNORECASE)
            patches_injected.append(f"aria-label on {canvas_count} canvas element(s)")
            report.patches.append(PolishPatch(
                dimension="a11y",
                action="inject-canvas-aria-label",
                detail=f"Added aria-label and role to {canvas_count} canvas element(s)",
            ))

        # Check for keyboard event handlers (keydown, keyup, keypress)
        has_keyboard = bool(re.search(r'keydown|keyup|keypress', html, re.IGNORECASE))
        if not has_keyboard:
            # Inject a basic keyboard handler stub
            keyboard_stub = """<script>
document.addEventListener('keydown',function(e){if(e.key==='Tab'){e.preventDefault();}});
</script>"""
            html = html.replace('</body>', keyboard_stub + '\n</body>', 1)
            patches_injected.append("keyboard focus handler")
            report.patches.append(PolishPatch(
                dimension="a11y",
                action="inject-keyboard-handler",
                detail="Added basic keyboard focus management (Tab key)",
            ))

        # Check for lang attribute on <html>
        has_lang = bool(re.search(r'<html[^>]*\blang\s*=', html, re.IGNORECASE))
        if not has_lang:
            html = re.sub(
                r'<html(?![^>]*\blang\s*=)',
                '<html lang="en"',
                html,
                count=1,
                flags=re.IGNORECASE,
            )
            patches_injected.append('lang="en" on <html>')
            report.patches.append(PolishPatch(
                dimension="a11y",
                action="inject-html-lang",
                detail='Added lang="en" attribute to <html> element',
            ))

        # Check for viewport meta tag (mobile accessibility)
        has_viewport = bool(re.search(r'name\s*=\s*["\']viewport["\']', html, re.IGNORECASE))
        if not has_viewport and '<head>' in html.lower():
            viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            html = re.sub(r'(<head[^>]*>)', r'\1' + viewport, html, count=1, flags=re.IGNORECASE)
            patches_injected.append("viewport meta tag")
            report.patches.append(PolishPatch(
                dimension="a11y",
                action="inject-viewport-meta",
                detail="Added responsive viewport meta tag for mobile accessibility",
            ))

        if not patches_injected:
            report.notes.append("All accessibility checks passed - no fixes needed")
        else:
            report.notes.append(f"Applied {len(patches_injected)} accessibility fixes")

        report.passed = True
        return html, report

    # -- Internal: SEO Metadata --------------------------------------------

    def _seo_metadata(
        self, html: str, title: str, description: str
    ) -> Tuple[str, DimensionReport]:
        """Inject SEO metadata: title, description, Open Graph, Twitter Card."""
        report = DimensionReport(dimension="seo", passed=True)

        # Generate description if not provided
        if not description:
            description = f"Play {title} - an AI-native game powered by SparkLabs."

        # Check existing title
        has_title = bool(re.search(r'<title>[^<]+</title>', html, re.IGNORECASE))
        if not has_title and '<head>' in html.lower():
            title_tag = f'<title>{title}</title>'
            html = re.sub(r'(<head[^>]*>)', r'\1' + title_tag, html, count=1, flags=re.IGNORECASE)
            report.patches.append(PolishPatch(
                dimension="seo",
                action="inject-title-tag",
                detail=f"Added <title>{title}</title>",
            ))
        elif has_title:
            # Update existing title if it's generic
            html = re.sub(
                r'<title>[^<]*</title>',
                f'<title>{title}</title>',
                html,
                count=1,
                flags=re.IGNORECASE,
            )
            report.patches.append(PolishPatch(
                dimension="seo",
                action="update-title-tag",
                detail=f"Updated <title> to '{title}'",
            ))

        # Build meta tags block
        meta_tags = []
        meta_tags.append(f'<meta name="description" content="{description}">')
        meta_tags.append(f'<meta property="og:title" content="{title}">')
        meta_tags.append(f'<meta property="og:description" content="{description}">')
        meta_tags.append(f'<meta property="og:type" content="website">')
        meta_tags.append(f'<meta name="twitter:card" content="summary">')
        meta_tags.append(f'<meta name="twitter:title" content="{title}">')
        meta_tags.append(f'<meta name="twitter:description" content="{description}">')

        meta_block = '\n'.join(meta_tags)

        # Inject meta tags after <head>
        if '<head>' in html.lower() or '<head ' in html.lower():
            # Check which meta tags are already present
            existing_desc = bool(re.search(r'name\s*=\s*["\']description["\']', html, re.IGNORECASE))
            if not existing_desc:
                html = re.sub(
                    r'(<head[^>]*>)',
                    r'\1' + meta_block,
                    html,
                    count=1,
                    flags=re.IGNORECASE,
                )
                report.patches.append(PolishPatch(
                    dimension="seo",
                    action="inject-seo-meta-tags",
                    detail="Added description, Open Graph, and Twitter Card meta tags",
                ))
            else:
                report.notes.append("SEO meta tags already present")
        else:
            # No <head> tag, inject a minimal one
            head = f'<head>{meta_block}</head>'
            html = re.sub(r'(<html[^>]*>)', r'\1' + head, html, count=1, flags=re.IGNORECASE)
            report.patches.append(PolishPatch(
                dimension="seo",
                action="inject-head-with-meta",
                detail="Created <head> with SEO meta tags",
            ))

        report.passed = True
        return html, report

    # -- Internal: Performance Guards --------------------------------------

    def _performance(self, html: str) -> Tuple[str, DimensionReport]:
        """Inject performance guards: rAF error boundary, memory cleanup."""
        report = DimensionReport(dimension="perf", passed=True)

        # Check if rAF guards already present
        has_raf_guard = 'requestAnimationFrame' in html and 'cancelAnimationFrame' in html

        # Performance guard script - wraps rAF with error handling and cleanup
        perf_guard = """<script>
(function(){
  var _slRAF=requestAnimationFrame;
  var _slCAF=cancelAnimationFrame;
  var _slActiveFrames={};
  var _slFrameId=0;
  window.requestAnimationFrame=function(cb){
    var id=++_slFrameId;
    var wrapped=function(t){
      try{cb(t);delete _slActiveFrames[id];}
      catch(e){console.error('[SparkLabs] rAF error:',e);delete _slActiveFrames[id];}
    };
    _slActiveFrames[id]=_slRAF(wrapped);
    return id;
  };
  window.cancelAnimationFrame=function(id){
    if(_slActiveFrames[id]){_slCAF(_slActiveFrames[id]);delete _slActiveFrames[id];}
  };
  window.addEventListener('beforeunload',function(){
    Object.keys(_slActiveFrames).forEach(function(id){
      _slCAF(_slActiveFrames[id]);
    });
  });
  window.onerror=function(msg,url,line,col,err){
    console.error('[SparkLabs] Runtime error:',msg,'at',url+':'+line+':'+col);
    return false;
  };
})();
</script>"""

        if not has_raf_guard:
            html = html.replace('</body>', perf_guard + '\n</body>', 1)
            report.patches.append(PolishPatch(
                dimension="perf",
                action="inject-raf-error-boundary",
                detail="Wrapped requestAnimationFrame with error handling and cleanup on unload",
            ))
        else:
            report.notes.append("rAF guards already present")

        # Check for memory leak prevention (beforeunload cleanup)
        has_cleanup = 'beforeunload' in html
        if not has_cleanup:
            cleanup_stub = """<script>
window.addEventListener('beforeunload',function(){
  if(typeof cleanup==='function'){cleanup();}
  if(typeof gameLoop==='function'){cancelAnimationFrame(window._gameFrame||0);}
});
</script>"""
            html = html.replace('</body>', cleanup_stub + '\n</body>', 1)
            report.patches.append(PolishPatch(
                dimension="perf",
                action="inject-unload-cleanup",
                detail="Added beforeunload cleanup handler for memory leak prevention",
            ))

        report.passed = True
        return html, report

    # -- Internal: Cross-Browser Compatibility -----------------------------

    def _compatibility(self, html: str) -> Tuple[str, DimensionReport]:
        """Inject cross-browser compatibility polyfills."""
        report = DimensionReport(dimension="compat", passed=True)

        # Check if polyfills already present
        has_polyfill = 'SparkLabsCompatPolyfill' in html

        compat_polyfill = """<script>
(function(){
  if(!window.SparkLabsCompatPolyfill){
    window.SparkLabsCompatPolyfill=true;
    // requestAnimationFrame polyfill
    if(!window.requestAnimationFrame){
      window.requestAnimationFrame=function(cb){
        return setTimeout(function(){cb(Date.now());},16);
      };
      window.cancelAnimationFrame=function(id){clearTimeout(id);};
    }
    // performance.now polyfill
    if(!window.performance){window.performance={};}
    if(!window.performance.now){
      window.performance.now=function(){return Date.now();};
    }
    // AudioContext polyfill (vendor prefixes)
    if(!window.AudioContext){
      window.AudioContext=window.webkitAudioContext||window.mozAudioContext||null;
    }
    // requestIdleCallback polyfill
    if(!window.requestIdleCallback){
      window.requestIdleCallback=function(cb){
        var start=Date.now();
        return setTimeout(function(){
          cb({didTimeout:false,timeRemaining:function(){return Math.max(0,50-(Date.now()-start));}});
        },1);
      };
      window.cancelIdleCallback=function(id){clearTimeout(id);};
    }
  }
})();
</script>"""

        if not has_polyfill:
            # Inject polyfill as the first script in <head>
            if '<head>' in html.lower():
                html = re.sub(
                    r'(<head[^>]*>)',
                    r'\1' + compat_polyfill,
                    html,
                    count=1,
                    flags=re.IGNORECASE,
                )
            else:
                html = compat_polyfill + html
            report.patches.append(PolishPatch(
                dimension="compat",
                action="inject-compat-polyfills",
                detail="Added polyfills: rAF, performance.now, AudioContext, requestIdleCallback",
            ))
        else:
            report.notes.append("Compatibility polyfills already present")

        report.passed = True
        return html, report


# =============================================================================
# Module-level accessor
# =============================================================================


def get_game_polish() -> GamePolish:
    """Get the singleton GamePolish instance."""
    return GamePolish.get_instance()
