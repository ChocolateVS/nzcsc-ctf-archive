FROM alpine:3.20
RUN apk add --no-cache openssh-server openssh-keygen \
 && ssh-keygen -A \
 && adduser -D -s /bin/sh vic \
 && adduser -D -s /bin/sh arteta \
 && mkdir -p /home/arteta/.ssh \
 && sed -i 's/^arteta:!:/arteta:*:/' /etc/shadow \
 && printf 'PasswordAuthentication no\nPermitRootLogin no\nAllowUsers arteta\nUseDNS no\n' >> /etc/ssh/sshd_config
COPY authorized_keys /home/arteta/.ssh/authorized_keys
RUN chown -R arteta:arteta /home/arteta/.ssh \
 && chmod 700 /home/arteta/.ssh \
 && chmod 600 /home/arteta/.ssh/authorized_keys
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
