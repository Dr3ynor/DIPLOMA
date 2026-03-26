from abc import ABC

class Subject(ABC):
    """Abstraktní třída pro objekt, který je sledován"""
    
    def __init__(self):
        self._observers = []

    def attach(self, observer_callback):
        self._observers.append(observer_callback)

    def detach(self, observer_callback):
        self._observers.remove(observer_callback)

    def notify(self, data):
        for observer in self._observers:
            observer(data)
