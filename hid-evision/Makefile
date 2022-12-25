ifneq ($(KERNELRELEASE),)
# kbuild part of makefile
obj-m  := hid-evision.o

else
# normal makefile

INSTALL_MOD_DIR := kernel/drivers/hid

KVERSION := $(shell uname -r)
KDIR := /lib/modules/$(KVERSION)/build

.PHONY: all modules clean install modules_install

all: modules

modules:
	@$(MAKE) -C $(KDIR) M=$(CURDIR) $@

clean:
	@$(MAKE) -C $(KDIR) M=$(CURDIR) $@

modules_install:
	@$(MAKE) -C $(KDIR) M=$(CURDIR) INSTALL_MOD_DIR=$(INSTALL_MOD_DIR) $@

install: modules_install
endif
