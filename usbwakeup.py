#!/usr/bin/python
# coding: utf-8
from collections import defaultdict
import os



SYSFS_USB_PATH = '/sys/bus/usb/devices/'
PROC_ACPI_WAKEUP_PATH = '/proc/acpi/wakeup'
DISABLED_STATE = 'disabled'
ENABLED_STATE = 'enabled'
PROC_ACPI_WAKEUP_CACHED = open(PROC_ACPI_WAKEUP_PATH).read()



class UsbDevice(object):
    busnum = None
    devpath = None
    manufacturer = None
    product = None
    wakeup = None
    root_hub = None

    def __init__(self, d, root_hub=None):
        self.root_hub = root_hub
        self.busnum = int(self.read_attr(d, 'busnum'))
        self.devpath = int(self.read_attr(d, 'devpath'))

        try:
            self.manufacturer = self.read_attr(d, 'manufacturer')
        except:
            self.manufacturer = self.read_attr(d, 'idVendor')

        try:
            self.product = self.read_attr(d, 'product')
        except:
            self.product = self.read_attr(d, 'idProduct')

        try:
            self.wakeup = self.read_attr(d, 'power/wakeup')
        except:
            self.wakeup = 'not supported'

    def __repr__(self):
        return '%s - %s (%s)' % (self.get_name(), self.get_full_device_number(), self.get_acpi_wakeup_description())

    def read_attr(self, dev, attr):
        try:
            return open(SYSFS_USB_PATH + dev + '/' + attr).read().rstrip()
        except:
            raise

    def get_full_device_number(self):
        return 'bus %d, device %d' % (self.busnum, self.devpath)

    def get_acpi_wakeup_description(self):
        if self.root_hub.proc_acpi_wakeup_state == DISABLED_STATE:
            return 'ACPI wakeup disabled on /proc/acpi/wakeup'
        elif self.root_hub.proc_acpi_wakeup_state == 'unknown':
            # ignore fact that device is not listed in /proc/acpi/wakeup, waking up may still work
            pass
        elif self.root_hub.wakeup != ENABLED_STATE:
            return 'ACPI wakeup disabled on root hub'
        return 'ACPI wakeup %s' % self.wakeup

    def is_wakup_enabled(self):
        return self.root_hub.proc_acpi_wakeup_state != DISABLED_STATE and \
        self.root_hub.wakeup == ENABLED_STATE and \
        self.wakeup == ENABLED_STATE


    def get_name(self):
        return '%s/%s' % (self.manufacturer, self.product)

    def get_change_state_description(self):
        if self.is_wakup_enabled():
            msg = '    Disable wakeup with:\n'
            msg += '    echo disabled > %susb%d/%d-%d/power/wakeup\n' % (SYSFS_USB_PATH, self.busnum, self.busnum, self.devpath)
        else:
            msg = '    Enable wakeup with:\n'
        if self.root_hub.proc_acpi_wakeup_state == DISABLED_STATE:
            msg += '    echo USB%d > %s\n' % (self.busnum, PROC_ACPI_WAKEUP_PATH)
        if self.root_hub.wakeup != ENABLED_STATE:
            msg += '    echo enabled > %susb%d/power/wakeup\n' % (SYSFS_USB_PATH, self.busnum)
        if self.wakeup == DISABLED_STATE:
            msg += '    echo enabled > %susb%d/%d-%d/power/wakeup\n' % (SYSFS_USB_PATH, self.busnum, self.busnum, self.devpath)
        return msg



class RootHubUsbDevice(UsbDevice):
    children = None
    proc_acpi_wakeup_state = None
    def __init__(self, *args, **kwargs):
        super(RootHubUsbDevice, self).__init__(*args, **kwargs)
        self.proc_acpi_wakeup_state = self.get_proc_acpi_wakeup_state()

    def get_proc_acpi_wakeup_state(self):
        for line in PROC_ACPI_WAKEUP_CACHED.split('\n'):
            if line.startswith('USB%d' % self.busnum):
                if '*enabled' in line:
                    return ENABLED_STATE
                elif '*disabled' in line:
                    return DISABLED_STATE
                else:
                    return 'unknown'
        return 'unknown'



class UsbWakeupLister(object):
    @classmethod
    def process(self):
        output = ''
        root_hubs = self.discover_devices()
        for hub_id in sorted(root_hubs.keys()):
            for device in root_hubs[hub_id].children:
                output += ' * %s\n' % device
                output += device.get_change_state_description()
        output += 'Hint: To make ACPI wakeup configuration permament, add mentioned commands to system startup script (for some distributions: /etc/rc.local)'
        return output

    @classmethod
    def discover_devices(self):
        root_hubs = defaultdict(dict)
        for d in os.listdir(SYSFS_USB_PATH):
            if not d.startswith('usb'):
                continue
            root_hub = RootHubUsbDevice(d)
            root_hub.children = []
            for d in os.listdir(SYSFS_USB_PATH + d):
                if self.is_device(d):
                    device = UsbDevice(d, root_hub)
                    root_hub.children.append(device)
            root_hubs[root_hub.busnum] = root_hub
        return root_hubs

    @classmethod
    def is_device(self, d):
        return d[0].isdigit() and ':' not in d



if __name__ == '__main__':
    print UsbWakeupLister.process()



