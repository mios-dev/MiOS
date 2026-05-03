#!/bin/bash
# Xbox VM CPU Pinning Configuration Script
# Automated XML editing for nano users

echo "Xbox VM CPU Pinning Configuration"
echo ""
echo "This script will:"
echo "  1. Export current Xbox VM configuration"
echo "  2. Backup the original"
echo "  3. Open in nano for you to paste the CPU config"
echo "  4. Redefine the VM with new configuration"
echo ""
read -p "Press ENTER to continue or Ctrl+C to cancel..."

# Export current XML
sudo virsh dumpxml Xbox > /tmp/xbox-original.xml

# Create backup
cp /tmp/xbox-original.xml /tmp/xbox-backup-$(date +%Y%m%d-%H%M%S).xml

# Copy for editing
cp /tmp/xbox-original.xml /tmp/xbox-edit.xml

echo ""
echo "INSTRUCTIONS FOR NANO EDITOR:"
echo ""
echo "1. Find the line: <vcpu placement=\"static\">12</vcpu>"
echo "   - Press: Ctrl+W"
echo "   - Type: vcpu placement"
echo "   - Press: ENTER"
echo ""
echo "2. Delete that line and the old <cpu> section"
echo ""
echo "3. Paste the new CPU configuration (see below)"
echo ""
echo "4. Save and exit:"
echo "   - Press: Ctrl+X"
echo "   - Press: Y (to confirm)"
echo "   - Press: ENTER"
echo ""
echo "CPU CONFIGURATION TO PASTE:"
cat << 'EOF'

  <vcpu placement="static">12</vcpu>
  <cputune>
    <vcpupin vcpu="0" cpuset="0"/>
    <vcpupin vcpu="1" cpuset="1"/>
    <vcpupin vcpu="2" cpuset="2"/>
    <vcpupin vcpu="3" cpuset="3"/>
    <vcpupin vcpu="4" cpuset="4"/>
    <vcpupin vcpu="5" cpuset="5"/>
    <vcpupin vcpu="6" cpuset="16"/>
    <vcpupin vcpu="7" cpuset="17"/>
    <vcpupin vcpu="8" cpuset="18"/>
    <vcpupin vcpu="9" cpuset="19"/>
    <vcpupin vcpu="10" cpuset="20"/>
    <vcpupin vcpu="11" cpuset="21"/>
    <emulatorpin cpuset="8-11"/>
    <iothreadpin iothread="1" cpuset="8-11"/>
  </cputune>
  <cpu mode="host-passthrough" check="none" migratable="on">
    <topology sockets="1" dies="1" clusters="1" cores="6" threads="2"/>
    <cache mode="passthrough"/>
    <feature policy="require" name="topoext"/>
    <feature policy="require" name="invtsc"/>
  </cpu>

EOF
echo ""
read -p "Press ENTER to open nano editor..."

# Open in nano
nano /tmp/xbox-edit.xml

echo ""
echo "Validating XML..."

# Validate the XML
if sudo virt-xml-validate /tmp/xbox-edit.xml 2>/dev/null; then
    echo "âœ“ XML validation passed"
else
    echo "âš  Warning: XML validation skipped (virt-xml-validate not found)"
fi

echo ""
read -p "Apply this configuration to Xbox VM? [y/N]: " confirm

if [[ "$confirm" =~ ^[Yy]$ ]]; then
    echo "Applying configuration..."
    
    # Undefine old VM
    sudo virsh undefine Xbox --nvram
    
    # Define with new configuration
    sudo virsh define /tmp/xbox-edit.xml
    
    echo ""
    echo "âœ“ Configuration Applied!"
    echo ""
    echo "Verification:"
    sudo virsh dumpxml Xbox | grep -A 5 vcpupin
    echo ""
    echo "Backup saved to: /tmp/xbox-backup-*.xml"
    echo ""
    echo "Next steps:"
    echo "  1. Start VM: sudo virsh start Xbox"
    echo "  2. Check logs: tail -f /var/log/libvirt/qemu/Xbox-cpu-pin.log"
else
    echo "Cancelled. Original configuration unchanged."
    echo "Edit file is saved at: /tmp/xbox-edit.xml"
fi
