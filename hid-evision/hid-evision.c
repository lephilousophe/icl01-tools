// SPDX-License-Identifier: GPL-2.0-or-later
/*
 *  HID driver for Evision devices
 *  For now, only ignore ignore bogus consumer reports
 *  sent after the keyboard has been configured
 *
 *  Copyright (c) 2022 Le Philousophe
 */

#include <linux/device.h>
#include <linux/input.h>
#include <linux/hid.h>
#include <linux/module.h>
#include <linux/usb.h>


#define USB_VENDOR_ID_EVISION       0x320f
#define USB_DEVICE_ID_EVISION_ICL01 0x5041

static int evision_input_mapping(struct hid_device *hdev, struct hid_input *hi,
		struct hid_field *field, struct hid_usage *usage,
		unsigned long **bit, int *max)
{
	if ((usage->hid & HID_USAGE_PAGE) != HID_UP_CONSUMER)
		return 0;

	// Ignore key down event
	if ((usage->hid & HID_USAGE) >> 8 == 0x05) {
		return -1;
	}
	if ((usage->hid & HID_USAGE) >> 8 == 0x06) {
		return -1;
	}
	switch (usage->hid & HID_USAGE) {
	case 0x0401: return -1;
	case 0x0402: return -1;
	}
	return 0;
}

static int evision_probe(struct hid_device *hdev, const struct hid_device_id *id)
{
	int ret;

	if (!hid_is_usb(hdev))
		return -EINVAL;

	ret = hid_parse(hdev);
	if (ret) {
		hid_err(hdev, "Evision hid parse failed: %d\n", ret);
		return ret;
	}

	ret = hid_hw_start(hdev, HID_CONNECT_DEFAULT);
	if (ret) {
		hid_err(hdev, "Evision hw start failed: %d\n", ret);
		return ret;
	}

	return 0;
}

static const struct hid_device_id evision_devices[] = {
	{ HID_USB_DEVICE(USB_VENDOR_ID_EVISION, USB_DEVICE_ID_EVISION_ICL01) },
	{ }
};
MODULE_DEVICE_TABLE(hid, evision_devices);

static struct hid_driver evision_driver = {
	.name = "evision",
	.id_table = evision_devices,
	.input_mapping = evision_input_mapping,
	.probe = evision_probe,
};
module_hid_driver(evision_driver);

MODULE_LICENSE("GPL");
