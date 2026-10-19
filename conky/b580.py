#!/usr/bin/env python3
import os
import glob
import time

# conky calls this script once per field every refresh; cache the result so
# the sysfs/fdinfo scan and power sampling only happen once per interval.
CACHE = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'conky-b580')
CACHE_TTL = 1.5

def get_b580_hwmon():
    for card in glob.glob('/sys/class/drm/card*'):
        dev = os.path.join(card, 'device')
        try:
            with open(os.path.join(dev, 'vendor')) as f:
                if f.read().strip() != '0x8086': continue
            with open(os.path.join(dev, 'device')) as f:
                if f.read().strip() != '0xe20b': continue
            
            for hw in glob.glob(os.path.join(dev, 'hwmon', 'hwmon*')):
                name_file = os.path.join(hw, 'name')
                if os.path.exists(name_file):
                    with open(name_file) as nf:
                        if nf.read().strip() == 'xe':
                            return dev, hw
        except:
            continue
    return None, None

def read_temp(hw, sensor_inputs):
    for t_file in sensor_inputs:
        p = os.path.join(hw, t_file)
        if os.path.exists(p):
            try:
                with open(p) as f:
                    val = int(f.read().strip()) // 1000
                    if val > 0:
                        return f"{val}°C"
            except:
                pass
    return "N/A"

def main():
    try:
        if time.time() - os.path.getmtime(CACHE) < CACHE_TTL:
            with open(CACHE) as f:
                print(f.read(), end='')
            return
    except OSError:
        pass

    line = collect()
    try:
        tmp = f"{CACHE}.{os.getpid()}"
        with open(tmp, 'w') as f:
            f.write(line + '\n')
        os.replace(tmp, CACHE)
    except OSError:
        pass
    print(line)

def collect():
    dev, hw = get_b580_hwmon()
    if not hw:
        return "N/A|N/A|N/A|N/A|12.0 GiB|12.0 GiB"

    # GPU Core Temp: try temp1_input (GT Core) first, fallback to temp2_input (Package)
    temp = read_temp(hw, ['temp1_input', 'temp2_input'])

    # VRAM Temp: try temp3_input
    vram_temp = read_temp(hw, ['temp3_input', 'temp4_input'])

    # Clock Frequency
    try:
        with open(os.path.join(dev, 'tile0', 'gt0', 'freq0', 'cur_freq')) as f:
            clock = f"{f.read().strip()} MHz"
    except:
        clock = "N/A"

    # Power (Instant energy delta)
    power = "N/A"
    e_path = os.path.join(hw, 'energy1_input')
    if os.path.exists(e_path):
        try:
            with open(e_path) as f: e1 = int(f.read().strip())
            t1 = time.time()
            time.sleep(0.1)
            with open(e_path) as f: e2 = int(f.read().strip())
            t2 = time.time()
            watts = ((e2 - e1) / 1000000.0) / (t2 - t1)
            power = f"{watts:.1f} W"
        except:
            pass

    # VRAM Usage from fdinfo
    vram_kib = 0
    for fd in glob.glob('/proc/[0-9]*/fdinfo/*'):
        try:
            with open(fd, 'r') as f:
                content = f.read()
                if 'drm-driver:\txe' in content or 'drm-driver: xe' in content:
                    for line in content.splitlines():
                        if line.startswith('drm-resident-vram0:'):
                            parts = line.split()
                            val = parts[1].replace('KiB', '')
                            vram_kib += int(val)
        except:
            continue

    vram_used = f"{vram_kib / 1048576:.1f} GiB"
    return f"{temp}|{vram_temp}|{clock}|{power}|{vram_used}|12.0 GiB"

if __name__ == '__main__':
    main()
