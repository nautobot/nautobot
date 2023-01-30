# SELinux Troubleshooting

When installing Nautobot for the first time on a Redhat-based Linux Distribution, SELinux may prevent the Nautobot stack from working properly. An example is SELinux preventing the HTTP daemon (NGINX, et al.) from communicating to the Django application stack on the backend.

## Determine if SELinux is the Culprit

An example of a broken application can be seen in the Nginx error logs below:

```no-highlight
sudo tail -f /var/log/nginx/error.log
```

Example output:

```no-highlight
2021/02/26 15:16:55 [crit] 67245#0: *494 connect() to 127.0.0.1:8080 failed (13: Permission denied) while connecting to upstream, client: 47.221.167.40, server: nautobot.example.com, request: "GET / HTTP/1.1", upstream: "http://127.0.0.1:8080/", host: "nautobot.example.com"
2021/02/26 15:16:56 [crit] 67245#0: *494 connect() to 127.0.0.1:8080 failed (13: Permission denied) while connecting to upstream, client: 47.221.167.40, server: nautobot.example.com, request: "GET /favicon.ico HTTP/1.1", upstream: "http://127.0.0.1:8080/favicon.ico", host: "nautobot.example.com", referrer: "https://nautobot.example.com/"
2021/02/26 15:16:58 [crit] 67245#0: *544 connect() to 127.0.0.1:8080 failed (13: Permission denied) while connecting to upstream, client: 47.221.167.40, server: nautobot.example.com, request: "GET / HTTP/1.1", upstream: "http://127.0.0.1:8080/", host: "nautobot.example.com"
2021/02/26 15:16:58 [crit] 67245#0: *544 connect() to 127.0.0.1:8080 failed (13: Permission denied) while connecting to upstream, client: 47.221.167.40, server: nautobot.example.com, request: "GET /favicon.ico HTTP/1.1", upstream: "http://127.0.0.1:8080/favicon.ico", host: "nautobot.example.com", referrer: "https://nautobot.example.com/"
```

A quick way to verify that SELinux is preventing the application from working is to first, verify that SELinux is indeed `enabled` and operating in `enforcing` mode, and second, temporarily put SELinux in `permissive` mode. With SELinux in `permissive` mode, the application stack can be tested again. If the application starts working as expected, then SELinux is most likely the culprit.

```no-highlight
# sestatus | egrep 'SELinux status|Current mode'
SELinux status:                 enabled
Current mode:                   enforcing
```

To put SELinux in `permissive` mode, execute the `setenforce` command with the `0` flag.

```no-highlight
# setenforce 0

# sestatus | egrep 'SELinux status|Current mode'
SELinux status:                 enabled
Current mode:                   permissive
```

With SELinux in `permissive` mode, test the application stack and ensure everything is working properly. If the application is working, put SELinux back into `enforcing` mode. This is done by executing the `setenforce` command with the `1` flag.

```no-highlight
# setenforce 1

# sestatus | egrep 'SELinux status|Current mode'
SELinux status:                 enabled
Current mode:                   enforcing
```

## Troubleshoot SELinux

Troubleshooting SELinux in most instances is straightforward. Using the `sealert` command to parse `/var/log/audit/audit.log` is the fastest way to pin-point SELinux specific issues. In many cases, `sealert` will also provide guidance as to how to resolve the issue.

```no-highlight
# sealert -a /var/log/audit/audit.log
100% done
found 1 alerts in /var/log/audit/audit.log
--------------------------------------------------------------------------------

SELinux is preventing /usr/sbin/nginx from name_connect access on the tcp_socket port 8080.

*****  Plugin connect_ports (85.9 confidence) suggests   *********************

If you want to allow /usr/sbin/nginx to connect to network port 8080
Then you need to modify the port type.
Do
# semanage port -a -t PORT_TYPE -p tcp 8080
    where PORT_TYPE is one of the following: dns_port_t, dnssec_port_t, kerberos_port_t, ocsp_port_t.

*****  Plugin catchall_boolean (7.33 confidence) suggests   ******************

If you want to allow httpd to can network connect
Then you must tell SELinux about this by enabling the 'httpd_can_network_connect' boolean.

Do
setsebool -P httpd_can_network_connect 1

*****  Plugin catchall_boolean (7.33 confidence) suggests   ******************

If you want to allow nis to enabled
Then you must tell SELinux about this by enabling the 'nis_enabled' boolean.

Do
setsebool -P nis_enabled 1

*****  Plugin catchall (1.35 confidence) suggests   **************************

If you believe that nginx should be allowed name_connect access on the port 8080 tcp_socket by default.
Then you should report this as a bug.
You can generate a local policy module to allow this access.
Do
allow this access for now by executing:
# ausearch -c 'nginx' --raw | audit2allow -M my-nginx
# semodule -X 300 -i my-nginx.pp


Additional Information:
Source Context                system_u:system_r:httpd_t:s0
Target Context                system_u:object_r:unreserved_port_t:s0
Target Objects                port 8080 [ tcp_socket ]
Source                        nginx
Source Path                   /usr/sbin/nginx
Port                          8080
Host                          <Unknown>
Source RPM Packages           nginx-1.14.1-9.module_el8.0.0+184+e34fea82.x86_64
Target RPM Packages
SELinux Policy RPM            selinux-policy-targeted-3.14.3-54.el8_3.2.noarch
Local Policy RPM              selinux-policy-targeted-3.14.3-54.el8_3.2.noarch
Selinux Enabled               True
Policy Type                   targeted
Enforcing Mode                Enforcing
Host Name                     nautobot.example.com
Platform                      Linux nautobot.example.com
                              4.18.0-240.1.1.el8_3.x86_64 #1 SMP Thu Nov 19
                              17:20:08 UTC 2020 x86_64 x86_64
Alert Count                   5
First Seen                    2021-02-26 15:16:55 UTC
Last Seen                     2021-02-26 15:23:12 UTC
Local ID                      b83bb817-85f6-4f5c-b6e0-eee3acc85504

Raw Audit Messages
type=AVC msg=audit(1614352992.209:585): avc:  denied  { name_connect } for  pid=67245 comm="nginx" dest=8080 scontext=system_u:system_r:httpd_t:s0 tcontext=system_u:object_r:unreserved_port_t:s0 tclass=tcp_socket permissive=0


type=SYSCALL msg=audit(1614352992.209:585): arch=x86_64 syscall=connect success=no exit=EACCES a0=12 a1=55d061477358 a2=10 a3=7ffc0c62296c items=0 ppid=67243 pid=67245 auid=4294967295 uid=988 gid=985 euid=988 suid=988 fsuid=988 egid=985 sgid=985 fsgid=985 tty=(none) ses=4294967295 comm=nginx exe=/usr/sbin/nginx subj=system_u:system_r:httpd_t:s0 key=(null)ARCH=x86_64 SYSCALL=connect AUID=unset UID=nginx GID=nginx EUID=nginx SUID=nginx FSUID=nginx EGID=nginx SGID=nginx FSGID=nginx

Hash: nginx,httpd_t,unreserved_port_t,tcp_socket,name_connect
```

In the first few lines of the audit, `sealert` details what SELinux is blocking and provides some options to remedy the issue.
Since Nginx is communicating with the Nautobot application via HTTP, the second option is the best option.

```no-highlight
SELinux is preventing /usr/sbin/nginx from name_connect access on the tcp_socket port 8080.

*****  Plugin connect_ports (85.9 confidence) suggests   *********************

If you want to allow /usr/sbin/nginx to connect to network port 8080
Then you need to modify the port type.
Do
# semanage port -a -t PORT_TYPE -p tcp 8080
    where PORT_TYPE is one of the following: dns_port_t, dnssec_port_t, kerberos_port_t, ocsp_port_t.

*****  Plugin catchall_boolean (7.33 confidence) suggests   ******************

If you want to allow httpd to can network connect
Then you must tell SELinux about this by enabling the 'httpd_can_network_connect' boolean.

Do
setsebool -P httpd_can_network_connect 1
```

Executing `setsebool -P httpd_can_network_connect 1` should remedy the issue. Verify this by executing the `setsebool` command, verify that SELinux is enabled and in `enforcing` mode via the `sestatus` command, and test the application stack for functionality.

The first curl command demonstrates the failure. Nginx responds with a HTTP response code of 502, indicating that it is unable to communicate with the Nautobot application. After executing the `setsebool` command, curl is used again to verify that Nginx is able to communicate with the Nautobot application. This is verified with the HTTP response code of 200.

```no-highlight
# curl -ik https://nautobot.example.com
HTTP/1.1 502 Bad Gateway
Server: nginx/1.14.1
Date: Fri, 26 Feb 2021 15:41:22 GMT
Content-Type: text/html
Content-Length: 173
Connection: keep-alive


# sestatus
SELinux status:                 enabled
SELinuxfs mount:                /sys/fs/selinux
SELinux root directory:         /etc/selinux
Loaded policy name:             targeted
Current mode:                   enforcing
Mode from config file:          enforcing
Policy MLS status:              enabled
Policy deny_unknown status:     allowed
Memory protection checking:     actual (secure)
Max kernel policy version:      32


# setsebool -P httpd_can_network_connect 1


# curl -ik https://nautobot.example.com
HTTP/1.1 200 OK
Server: nginx/1.14.1
Date: Fri, 26 Feb 2021 15:41:49 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 18698
Connection: keep-alive
X-Content-Type-Options: nosniff
Referrer-Policy: same-origin
X-Frame-Options: DENY
Vary: Cookie, Origin
```
