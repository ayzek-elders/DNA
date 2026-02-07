"""Abstract base classes for extensibility."""

from dna_core.engine.interfaces.i_processor import IProcessor
from dna_core.engine.interfaces.i_middleware import IMiddleware
from dna_core.engine.interfaces.i_observer import IObserver
from dna_core.engine.interfaces.i_subject import ISubject
from dna_core.engine.interfaces.i_lifecycle import ILifecycle

__all__ = ["IProcessor", "IMiddleware", "IObserver", "ISubject", "ILifecycle"]
