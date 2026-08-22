<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines filesystem permissions and ownership for the mios-llm-light lane (WS-10) state directories, specifically for storing per-conversation KV paging files in /var/lib/mios/llamacpp/slots.
AI-related: /usr/share/mios/llamacpp/models, /usr/libexec/mios/mios-models-firstboot, mios-llamacpp, mios-services
/usr/lib/tmpfiles.d/mios-llamacpp.conf
Writable state for the mios-llm-light lane (WS-10), owned by mios-llamacpp (827,
declared in usr/lib/sysusers.d/50-mios-services.conf). The GGUF model store
/usr/share/mios/llamacpp/models is build-baked (immutable composefs surface);
only the writable /var dirs are declared here (Architectural Law 2). The slots
dir holds per-conversation KV save files (_kv_paging / --slot-save-path).

<!-- mios-src:40e623f8494e from usr/lib/tmpfiles.d/mios-llamacpp.conf:1-8 -->

