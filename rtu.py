#!/usr/bin/env python3

RTU_TYPES = [
    'SOURCE',
    'TRANSMISSION',
    'LOAD'
]

RTU_SOURCE = 0
RTU_TRANSMISSION = 1
RTU_LOAD = 2

class RTU:

    def __init__(self, **kwargs):
        fields = ['guid', 'type']
        if any(k not in kwargs.keys() or not isinstance(kwargs[k], int) for k in fields):
            raise AttributeError()
        self.__guid = kwargs['guid']
        self.__type = kwargs['type']

    @property
    def guid(self) -> int:
        return self.__guid

    @guid.setter
    def guid(self, new_guid: int):
        self.__guid = new_guid

    @property
    def rtutype(self) -> int:
        return self.__type

    @rtutype.setter
    def rtutype(self, new_type: int):
        self.__type = new_type

    def loop(self):
        'Override this'
    
    def __str__(self):
        return 'RTU\r\n------------------\r\nID: {0:11d}\r\nType: {1:12s}'.format(self.__guid, RTU_TYPES[self.__type])
    
    def __repr__(self):
        return 'RTU({0:d}, {1:d})'.format(self.__guid, self.__type)

class Source(RTU):

    def __init__(self, **kwargs):
        super(Source, self).__init__(**kwargs)
        if 'voltage' not in kwargs.keys() or not isinstance(kwargs['voltage'], float):
            raise AttributeError()
        self.__voltage = kwargs['voltage']

    @property
    def voltage(self) -> float:
        return self.__voltage

    @voltage.setter
    def voltage(self, value: float):
        self.__voltage = value
    
    def __str__(self):
        return 'Source RTU\r\n----------------\r\nID: {0:11d}\r\nVout: {1:6.2f}'.format(self.guid, self.__voltage)
    
    def __repr__(self):
        return 'Source RTU ({0:d}, {1:.2f})'.format(self.guid, self.__voltage)

class Transmission(RTU):

    def __init__(self, **kwargs):
        super(Transmission, self).__init__(**kwargs)
        if any(k not in kwargs.keys() for k in ['state', 'states', 'loads', 'left', 'right']):
            raise AttributeError()
        if any(not isinstance(kwargs[k], int) for k in ['state', 'left', 'right']) or any(not isinstance(kwargs[k], list) for k in ['states', 'loads']):
            raise AttributeError()
        self.__state = kwargs['state']
        self.__loads = kwargs['loads']
        self.__left = kwargs['left']
        self.__right = kwargs['right']
        self.__load = None
        self.__vin = None
        self.__vout = None
        self.__amp = None

    @property
    def load(self) -> float:
        return self.__load

    @load.setter
    def load(self, value: float):
        self.__load = value

    def calculate_load(self):
        self.__load = -1
        for i in range(len(self.__loads)):
            if (state & (2 ** i)) > 0:
                if self.__loads[i] == 0:
                    self.__load = 0 # Failure
                    return
                self.__load = self.__loads[i] if self.__load == -1 else (self.__load * self.__loads[i]) / (self.__load + self.__loads[i])

class Load(RTU):

    def __init__(self, **kwargs):
        super(Load, self).__init__(**kwargs)
        if 'load' not in kwargs.keys() or not isinstance(kwargs['load'], float):
            raise AttributeError()
        self.__load = kwargs['load']

    @property
    def load(self) -> float:
        return self.__load

    @load.setter
    def load(self, new_load: float):
        self.__load = new_load

    def __str__(self):
        return 'Load RTU\r\n-------------------\r\nID: {0:14d}\r\nLoad: {1:9.2f}'.format(self.guid, self.__load)
    
    def __repr__(self):
        return 'Load RTU ({0:d}, {1:.2f})'.format(self.guid, self.__load)

