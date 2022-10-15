import time
from pynvraw import api, NvError, get_phys_gpu, nvapi_api, Clocks, get_gpus
from pynvraw.cuda_api import get_cuda_bus_slot


# Find all nvidia gpus in the system

def get_all_gpus():
    """Reads and returns all available nvidia gpus connected to the system as a dictionary"""
    all_gpus_by_bus_slot = {}
    cuda_bus_slot = 0
    while True:
        try:
            gpu = get_phys_gpu(cuda_bus_slot)
            all_gpus_by_bus_slot[gpu.name] = cuda_bus_slot
            cuda_bus_slot += 1
        except ValueError:
            return all_gpus_by_bus_slot


def get_gpu_readings(cuda_bus_slot: int):
    """Reads and returns the given gpu properties as a dictionary nested in a dictionary"""
    gpu = get_phys_gpu(cuda_bus_slot)
    gpu_readings = {cuda_bus_slot:
                        {'name': gpu.name,
                         'current_clocks': gpu.get_freqs('current'),
                         'base_clocks': gpu.get_freqs('base'),
                         'offset_clocks': gpu.get_overclock(),
                         'core_voltage': api.get_core_voltage(gpu.handle),
                         'core_temp': gpu.core_temp,
                         'hotspot_temp': gpu.hotspot_temp,
                         'vram_temp': gpu.vram_temp,
                         'fan_speed': gpu.fan,
                         'memory_total': gpu.memory_total,
                         'ram_type': gpu.ram_type,
                         'power_current%': gpu.power,
                         'power_limit%': gpu.power_limit,
                         'power_total': get_power(cuda_bus_slot)['PowerRailType.IN_TOTAL_BOARD'][0]
                         }}
    # print(f'{gpu.name}: core={gpu.core_temp} hotspot={gpu.hotspot_temp} vram={gpu.vram_temp}')
    # print(f'{gpu.name}: fan={gpu.fan}%')
    return gpu_readings


def gpu_core_memory(gpu_readings: dict):
    """Reads and returns the absolute core and memory timings of the given gpu"""
    clock_list = list(gpu_readings.values())[0]
    clock = clock_list['current_clocks']  # This returns Clocks class, which contains core and memory timings
    core = clock.core
    memory = clock.memory
    return float(core), float(memory)


def get_core_memory_offset(cuda_bus_slot: int):
    """Reads and returns the core and memory offset of the given gpu"""
    gpu = get_phys_gpu(cuda_bus_slot)
    gpu_clock_delta = gpu.get_overclock()
    core = gpu_clock_delta.core.current
    memory = gpu_clock_delta.memory.current
    return float(core), float(memory)


def get_power(cuda_bus_slot: int):
    """Reads and returns power consumption"""
    gpu = get_phys_gpu(cuda_bus_slot)
    power_dict = {}
    for rails, powers in gpu.get_rail_powers().items():
        power_dict[f'{rails!s}'] = [power.power for power in powers]
    return power_dict  # First item is Total board consumption in Watts


def gpu_overclock(cuda_bus_slot: int, memory=None, core=None):
    """
    Overclocks the given gpu based on the given memory and core values
    Mind that the values should be offsets, not absolute values.
    If None, then no overclocked value will be implemented
    :param cuda_bus_slot: int
    :param memory: None or float
    :param core: None or float
    """
    gpu = get_phys_gpu(cuda_bus_slot)
    if memory and core:
        try:
            gpu.set_overclock(Clocks(core=float(core), memory=float(memory), processor=0, video=0))
        except ValueError as er:
            print(f'Invalid memory or/and core offset given: {er}.  >> No overclock is set.')
        except TypeError as er:
            gpu.set_overclock(Clocks(core=None, memory=None, processor=0, video=0))
            print(f'TypeError: {er}. >> No overclock is set.')
    elif not memory or core:  # If one of them is None
        if memory:  # If memory is not None
            try:
                gpu.set_overclock(Clocks(core=None, memory=float(memory), processor=0, video=0))
            except ValueError as er:
                print(f'Invalid memory offset given: {er}.  >> No overclock is set.')
            except TypeError as er:
                gpu.set_overclock(Clocks(core=None, memory=None, processor=0, video=0))
                print(f'TypeError: {er}. >> No overclock is set.')
        elif core:  # Else if core is not None
            try:
                gpu.set_overclock(Clocks(core=float(core), memory=None, processor=0, video=0))
            except ValueError as er:
                print(f'Invalid core offset given: {er}.  >> No overclock is set.')
            except TypeError as er:
                gpu.set_overclock(Clocks(core=None, memory=None, processor=0, video=0))
                print(f'TypeError: {er}. >> No overclock is set.')


# gpu.set_overclock(Clocks(core=-275, memory=349, processor=0, video=0))
# print(get_all_gpus())
# get_cuda_bus_slot(0)
if __name__ == "__main__":
    # Get the drivers version
    print(f'Driver\'s version: {api.get_driver_version()[0]}')
    get_all_gpus = get_all_gpus()
    gpu = list(get_all_gpus.values())  # A list with all the bus slots
    gpu0 = get_gpu_readings(gpu[0])  # The first bus slot
    print(gpu0)
    print(gpu_core_memory(gpu0))
    # offset = get_core_memory_offset(gpu[0])
    print(get_core_memory_offset(gpu[0]))
    # gpu_overclock(gpu[0], memory='349.999', core='200')
    # gpu_overclock(gpu[0], memory=0, core=-275)
    # gpu_overclock(gpu[0], memory=530, core=200)
    # gpu_overclock(gpu[0], memory='a', core='a')
    print(get_core_memory_offset(gpu[0]))
    # print(gpu_core_memory(get_gpu_readings(gpu[0])))
    time.sleep(2)
