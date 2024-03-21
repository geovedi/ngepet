# Tuning Ubuntu

modify `/etc/sysctl.conf`,

```
vm.swappiness=10
vm.vfs_cache_pressure=50
net.core.rmem_max=16777216
net.core.wmem_max=16777216
fs.file-max=2097152
```

activate with:
`sudo sysctl -p`
