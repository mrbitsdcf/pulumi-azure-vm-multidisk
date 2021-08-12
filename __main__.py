"""An Azure RM Python Pulumi program"""

import base64
import pulumi
from pulumi_azure_native import storage
from pulumi_azure_native import resources
from pulumi_azure_native import network
from pulumi_azure_native import compute
from pulumi import Config
from pulumi import Output
from pulumi import export

# Using, but not managing, an Azure Resource Group

vm_name = 'vm-multiple-disks'

resource_group = resources.ResourceGroup.get(
    'resource_group',
    '/subscriptions/cd38513f-a52c-44fe-8ef7-3dbaa96b33a0/resourceGroups/claro-nba-tecnico-dev'
)

# Create an Azure resource (Storage Account)
account = storage.StorageAccount(
    'sprsharedstghmlg',
    resource_group_name=resource_group.name,
    sku=storage.SkuArgs(
        name=storage.SkuName.STANDARD_LRS,
    ),
    kind=storage.Kind.STORAGE_V2
)

# Export the primary key of the Storage Account
primary_key = pulumi.Output.all(resource_group.name, account.name) \
    .apply(lambda args: storage.list_storage_account_keys(
        resource_group_name=args[0],
        account_name=args[1]
    )).apply(lambda accountKeys: accountKeys.keys[0].value)

pulumi.export("primary_storage_key", primary_key)

# net = network.VirtualNetwork(
#     "vnet-claro-nba-tecnico",
#     resource_group_name=resource_group.name,
#     address_space=network.AddressSpaceArgs(
#         address_prefixes=["10.77.0.0/16"],
#     ),
#     subnets=[
#         network.SubnetArgs(name="subnet-claro-nba-tecnico-1", address_prefix="10.77.0.0/24"),
#         network.SubnetArgs(name="subnet-claro-nba-tecnico-2", address_prefix="10.77.1.0/24"),
#         network.SubnetArgs(name="subnet-claro-nba-tecnico-3", address_prefix="10.77.2.0/24"),
#         network.SubnetArgs(name="subnet-claro-nba-tecnico-4", address_prefix="10.77.3.0/24"),
#     ])

net = network.VirtualNetwork.get(
    "net",
    "/subscriptions/cd38513f-a52c-44fe-8ef7-3dbaa96b33a0/resourceGroups/claro-nba-tecnico-dev/providers/Microsoft.Network/virtualNetworks/vnet-claro-nba-tecnico-eastus"
)

public_ip = network.PublicIPAddress(
    "pubip-{0}".format(vm_name),
    resource_group_name=resource_group.name,
    public_ip_allocation_method=network.IPAllocationMethod.STATIC
)

network_iface = network.NetworkInterface(
    "nic-{0}".format(vm_name),
    resource_group_name=resource_group.name,
    ip_configurations=[
        network.NetworkInterfaceIPConfigurationArgs(
            name="privip-vm-multiple-disks",
            subnet=network.SubnetArgs(id=net.subnets[0].id),
            private_ip_allocation_method=network.IPAllocationMethod.DYNAMIC,
            public_ip_address=network.PublicIPAddressArgs(id=public_ip.id),
        )
    ]
)

username = 'ubuntu'
# Changing to the default password according with the documentation
# https://www.youtube.com/watch?v=0Jx8Eay5fWQ
password = 'god'

vm = compute.VirtualMachine(
    vm_name,
    resource_group_name=resource_group.name,
    network_profile=compute.NetworkProfileArgs(
        network_interfaces=[
            compute.NetworkInterfaceReferenceArgs(id=network_iface.id),
        ],
    ),
    hardware_profile=compute.HardwareProfileArgs(
        vm_size=compute.VirtualMachineSizeTypes.STANDARD_D2S_V3,
    ),
    os_profile=compute.OSProfileArgs(
        computer_name=vm_name,
        admin_username=username,
        admin_password=password,
        linux_configuration=compute.LinuxConfigurationArgs(
            disable_password_authentication=False,
        ),
    ),
    storage_profile=compute.StorageProfileArgs(
        os_disk=compute.OSDiskArgs(
            create_option=compute.DiskCreateOptionTypes.FROM_IMAGE,
            name="{0}-OsDisk".format(vm_name),
        ),
        data_disks=[
            compute.DataDiskArgs(
                create_option="Empty",
                disk_size_gb=64,
                lun=0,
            ),
            compute.DataDiskArgs(
                create_option="Empty",
                disk_size_gb=64,
                lun=1,
            ),
        ],
        image_reference=compute.ImageReferenceArgs(
            publisher="Canonical",
            offer="0001-com-ubuntu-server-focal",
            sku="20_04-lts",
            version="20.04.202005010",
        ),
    ))

combined_output = Output.all(vm.id, public_ip.name, resource_group.name)
public_ip_addr = combined_output.apply(
    lambda lst: network.get_public_ip_address(
        public_ip_address_name=lst[1],
        resource_group_name=lst[2]))
export("public_ip", public_ip_addr.ip_address)
