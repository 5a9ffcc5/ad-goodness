#!/bin/bash -x
# A simple wrapper for ldapsearch that will dump an entire AD in a simple .ldif
# file. You will have to make some specific changes :
# 
#   1. change the destination path
#   2. set your AD username in the environment variable uuu
#   3. set your AD password in the environment variable ppp
#   4. set your nearest AD Domain Controller IP in place of the IP below
#
# To find the nearest DC, a protip is to perform a DNS query for the domain
# name, here : client.com , and perform reverse DNS (PTR) lookups for all
# those IP addresses. You'll find that the DC are named with a prefix containing
# a country ID, which is nice because you want to dump the ~2Go of data from a
# server close to you.
#
#        ⚠
#       ╱ ╲
#      ╱   ╲
#     ╱     ╲
#    ╱       ╲      YOUR PASSWORD WILL BE EXPOSED
#   ╱ WARNING ╲
#  ╱           ╲
# ╱_____________╲
# ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
#
# Your password will be shown by the bash -x option. If you don't want to expose
# your password to shouldersurfing or screenshots, consider launching this
# script with /bin/bash ./script.sh, or remove the '-x' on first line. But what
# you should really do is find out how to give credentials in a secure fashion
# to ldapsearch. As it depends on your ldapsearch version (I'm lying) I did not
# look for other solutions.
#
# Once again, you'll expose your password to:
#  - Screenshots
#  - Shouldersurfing
#  - Command line auditing
#  - Shell history storage
#
# You have been warned.
#
ts=$(date "+%Y-%m-%d-%H-%M-%S")
target="/some/path/ad_dump.${ts}.ldif"
config_DC_IP="10.0.0.1"
config_DOMAIN="CLIENT"
config_LDAP_SCOPE="DC=CLIENT,DC=COM"

ldapsearch -h ${config_DC_IP} -x -D "${config_DOMAIN}\\${uuu}" -w ${ppp} \
  -b ${config_LDAP_SCOPE} -E pr=1000/noprompt -o ldif-wrap=no > ${target} &

# Prints the file growing speed.
speedometer -f ${target}
