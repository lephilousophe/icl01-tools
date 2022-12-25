Ironclad v2 Linux tools
=======================

A set of tools to customize ICL01 from Linux when used with its default (aka. Evision) firmware.

WARNING: These pieces of software come with NO WARRANTY!

icl01.py
--------

A basic Python library which can be used to fully customize the Ironclad.

This may work under Windows and MacOS X but this has not been tested.

This libray may work with other Evision keyboards but this has never been tested.

hid-evision
-----------

When the ICL01 is customized, it generates spurious HID events at each key event to inform Evision software about internal events.
Sadly, this is buggy as the reports overlap with perfectly valid reports which are considered by Linux and generate ghost key events.

This kernel module filters out these events to avoid them spamming userspace with these bogus key events.

Module can be built using the following commands:

* make clean
* make
* sudo make install

Additionally, the module can be installed using DKMS:

* sudo dkms add hid-evision
* sudo dkms build -m hid-evision/0.1
* sudo dkms install -m hid-evision/0.1

Once these commands are executed, the module will get recompiled at every kernel update.
