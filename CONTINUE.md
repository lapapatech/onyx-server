# Onyx — Continuar tras reinicio (2026-05-23)

## Última sesión: Gemini/Anthropic deep purge + sync Linear

Se completó el purge de Gemini/Anthropic del CLI Onyx. El bundle ya no filtra
nombres de proveedores muertos al usuario.

## Para retomar

Cargar contexto:
- `~/proyectos/onyx-server/CHECKPOINT.md` — estado completo del backend
- Skills: `onyx-cli` (proyecto CLI), `linear` (API)

## Repos

| Repo | Ruta | Rama |
|------|------|------|
| onyx (CLI) | ~/proyectos/onyx/ | main |
| onyx-server | ~/proyectos/onyx-server/ | main |

## Producción

- URL: https://onyx.devnullbox.net
- VPS: 51.222.84.105 (debian / Nodata7814!)
- Systemd: onyx-server.service (enabled)
- Master key: /tmp/onyx_key.txt
- npm: @onyxhq/onyx v0.1.0 (public)

## Trabajo de esta sesión (completado)

### Linear sincronizado ✅
- ONY-22 "Instalador one-liner curl|bash" → Done
- ONY-23 "Rotación de modelos falsos" → Done

### Gemini/Anthropic purge — 45+ archivos modificados ✅

**Código funcional muerto (0 refs en bundle):**
- GeminiContentGenerator / AnthropicContentGenerator eliminados
- AuthType.USE_GEMINI / USE_ANTHROPIC / USE_VERTEX_AI borrados de todos los archivos
- GEMINI_API_KEY / ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL eliminados
- Backend main.py: "gemini_advanced" eliminado de fake billing

**UI limpia (0 fugas user-facing):**
- Sin opciones "Gemini"/"Anthropic" en auth/providers (ProviderSetupSteps, customProvider, ModelDialog, config.js)
- Sin labels en AccountInfoDialog (.tsx + .js)
- Sin i18n de errores Anthropic (8 locales limpiados)
- originSource = 'OnyxCode' en vez de 'Gemini'/'Claude' (extensionManager)
- ExtensionOriginSource type: 'OnyxCode' | 'Claude' (sin 'Gemini')
- DEFAULT_ENV_KEYS, sandbox GEMINI_API_KEY passthrough, systemInfo — todo limpio
- geminiChat JSDoc: deepseek-v4-flash en vez de gemini-2.0-flash

**Archivos clave modificados:**
- `packages/core/src/core/contentGenerator.ts/.js` (ya estaba)
- `packages/core/src/core/openaiContentGenerator/converter.ts/.js` (renombres internos + fix responseId + fix error PDF)
- `packages/core/src/core/baseLlmClient.ts/.js` (fast auth array)
- `packages/core/src/models/constants.js` (AUTH_ENV_MAPPINGS)
- `packages/core/src/models/content-generator-config.ts/.js/.d.ts`
- `packages/core/src/config/config.ts/.d.ts` (ExtensionOriginSource)
- `packages/core/src/extension/extensionManager.ts/.js` (originSource)
- `packages/core/src/utils/errorParsing.ts/.js`
- `packages/core/src/core/geminiChat.ts/.js/.d.ts` (JSDoc)
- `packages/cli/src/config/config.js` (auth-type choices)
- `packages/cli/src/config/auth.js` (DEFAULT_ENV_KEYS + validación)
- `packages/cli/src/utils/modelConfigUtils.js` (detección env vars)
- `packages/cli/src/utils/systemInfo.js` (contentGeneratorConfig)
- `packages/cli/src/utils/sandbox.ts/.js` (GEMINI_API_KEY passthrough)
- `packages/cli/src/utils/apiPreconnect.ts/.js`
- `packages/cli/src/ui/commands/arenaCommand.ts/.js`
- `packages/cli/src/ui/auth/ProviderSetupSteps.js` (provider options)
- `packages/cli/src/ui/auth/useProviderSetupFlow.js` (DEFAULT_BASE_URLS)
- `packages/cli/src/ui/auth/useAuth.js`
- `packages/cli/src/ui/auth/providers/custom/customProvider.js`
- `packages/cli/src/ui/components/ModelDialog.js` (authTypeOrder)
- `packages/cli/src/ui/models/availableModels.js`
- `packages/cli/src/serve/httpAcpBridge.ts/.js` (comentario)
- `packages/vscode-ide-companion/src/webview/components/AccountInfoDialog.tsx/.js`
- `packages/vscode-ide-companion/src/utils/tokenLimits.ts/.js` (gemini patterns)
- `packages/sdk-typescript/src/types/protocol.d.ts/.ts` (AuthType)
- `packages/sdk-typescript/src/types/queryOptionsSchema.ts/.js/.d.ts`
- i18n: en.js, es.js, fr.js, ca.js, de.js, pt.js, ru.js, ja.js, zh.js, zh-TW.js
- `onyx-server/backend/main.py` (gemini_advanced)

### Lo que NO se tocó (estructural, no user-facing)

4 referencias a `gemini-2.0-flash` en JSDoc de `GenerateContentResponse` dentro del
paquete `@google/genai` (types solamente — 230+ imports son `import type { Content }`).
Eliminarlo requiere refactorizar el sistema de tipos/agentes completo. No es una fuga
al usuario final, solo JSDoc interno.

## Para desplegar los cambios

```bash
# 1. Rebuild del CLI
cd ~/proyectos/onyx
npm run build && npm run bundle

# 2. Desplegar backend si cambió main.py
cd ~/proyectos/onyx-server
git diff  # revisar cambios
# Si hay cambios en backend/:
ssh debian@51.222.84.105 'cd /home/debian/proyectos/onyx-server && git pull && sudo systemctl restart onyx-server'

# 3. Publicar npm si se quiere
cd ~/proyectos/onyx
npm run prepare:package && cd dist && npm publish --access public
```

## Commits pendientes

Hay cambios sin commitear en ambos repos. Hacer commit con mensaje descriptivo:
```
feat: deep purge of Gemini/Anthropic references from CLI bundle
```

## Próximas ideas (no priorizadas)

- Publicar versión limpia en npm
- Testing end-to-end con un target real
- Dashboard web para leer logs (ONY-19)
- Añadir más variantes de prompt injection honeypot
