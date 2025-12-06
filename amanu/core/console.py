import logging
import sys
from typing import Optional, ContextManager
from contextlib import contextmanager

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.traceback import install as install_rich_traceback
from rich.theme import Theme

# Custom theme
amanu_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
})

class ConsoleManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConsoleManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        
        self.console = Console(theme=amanu_theme)
        self.output_mode = "standard"
        self.initialized = True
        
        # Install rich traceback handler globally for unhandled exceptions
        # We will suppress this visually in standard mode via our own handling, 
        # but it's good to have available.
        install_rich_traceback(console=self.console, show_locals=False)

    def configure(self, output_mode: str = "standard", debug: bool = False):
        """
        Configure the console manager based on settings.
        output_mode: 'standard', 'verbose', 'silent'
        """
        self.output_mode = output_mode.lower()
        if debug:
            self.output_mode = "verbose"
            
        # Configure root logger
        logging.basicConfig(
            level=logging.NOTSET,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=self.console, rich_tracebacks=True, markup=True)]
        )
        
        # Adjust logging levels based on mode
        logger = logging.getLogger("Amanu")
        if self.output_mode == "silent":
            logger.setLevel(logging.CRITICAL)
        elif self.output_mode == "verbose":
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    def print(self, *args, **kwargs):
        if self.output_mode != "silent":
            self.console.print(*args, **kwargs)

    def log(self, message: str, style: str = "info"):
        if self.output_mode == "silent":
            return
        self.console.print(message, style=style)

    def success(self, message: str):
        if self.output_mode != "silent":
            self.console.print(f"✅ {message}", style="success")

    def warning(self, message: str):
        if self.output_mode != "silent":
            self.console.print(f"⚠️ {message}", style="warning")
            
    def error_panel(self, message: str, title: str = "Error"):
        if self.output_mode != "silent":
            self.console.print(Panel(message, title=title, border_style="red", expand=False))

    def verbose_error(self, stage: str, error: Exception, context: dict = None):
        """
        Output detailed error information in a format easy to copy for AI debugging.
        Only shown in verbose mode.
        """
        if self.output_mode != "verbose":
            return
        
        import traceback
        import datetime
        
        tb = traceback.format_exc()
        timestamp = datetime.datetime.now().isoformat()
        
        context_str = self._format_context(context) if context else 'No additional context'
        
        error_block = f"""
=== AMANU ERROR REPORT ===
Timestamp: {timestamp}
Stage: {stage}
Error Type: {type(error).__name__}
Error Message: {str(error)}

Context:
{context_str}

Traceback:
{tb}
=== END ERROR REPORT ===
"""
        self.console.print(error_block, style="dim")
    
    def _format_context(self, context: dict) -> str:
        """Format context dict for error report."""
        lines = []
        for key, value in context.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    @contextmanager
    def status(self, message: str) -> ContextManager:
        """
        Show a spinner status in standard mode.
        In verbose mode, just log start/end.
        In silent mode, do nothing.
        """
        if self.output_mode == "silent":
            yield
            return

        if self.output_mode == "verbose":
            self.console.log(f"Started: {message}")
            try:
                yield
            finally:
                self.console.log(f"Finished: {message}")
            return

        # Standard mode
        with self.console.status(f"[bold cyan]{message}", spinner="dots"):
            yield

# Global instance
console = ConsoleManager()
