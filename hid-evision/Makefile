ifneq ($(KERNELRELEASE),)
# kbuild part of makefile
obj-m  := hid-evision.o

else
# normal makefile

DRIVER := hid-evision
MOD_SUBDIR := drivers/hid

ifndef TARGET
TARGET = $(shell uname -r)
endif

KERNEL_MODULES ?= /lib/modules/$(TARGET)
KERNEL_BUILD ?= $(KERNEL_MODULES)/build

MODDESTDIR = $(KERNEL_MODULES)/kernel/$(MOD_SUBDIR)

# SYSTEM_MAP = $(KERNEL_BUILD)/System.map
ifneq ("","$(wildcard /boot/System.map-$(TARGET))")
SYSTEM_MAP = /boot/System.map-$(TARGET)
else
# Arch
SYSTEM_MAP = /proc/kallsyms
endif

MAKEFLAGS += --no-print-directory

ifneq ("","$(wildcard $(MODDESTDIR)/*.ko.gz)")
COMPRESS_GZIP := y
endif
ifneq ("","$(wildcard $(MODDESTDIR)/*.ko.xz)")
COMPRESS_XZ := y
endif

.PHONY: all modules clean install modules_install

all: modules

modules:
	@$(MAKE) -C $(KERNEL_BUILD) M=$(CURDIR) $@

clean:
	@$(MAKE) -C $(KERNEL_BUILD) M=$(CURDIR) $@

install: modules_install

modules_install:
	mkdir -p $(MODDESTDIR)
	cp $(DRIVER).ko $(MODDESTDIR)/
ifeq ($(COMPRESS_GZIP), y)
	@gzip -f $(MODDESTDIR)/$(DRIVER).ko
endif
ifeq ($(COMPRESS_XZ), y)
	@xz -f $(MODDESTDIR)/$(DRIVER).ko
endif
	depmod -a -F $(SYSTEM_MAP) $(TARGET)

endif
