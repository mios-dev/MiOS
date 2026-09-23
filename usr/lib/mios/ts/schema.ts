// AI-hint: Global TypeScript schemas and structural contracts for MiOS AIOS, covering OpenAI-compatible wire formats, mios.toml SSOT definitions, native metadata, and hardware-obfuscated Blade abstractions.
// AI-related: usr/lib/mios/schemas/ai_metadata.schema.json, usr/lib/mios/agent-pipe/mios_mcp_schema.py, usr/share/mios/mios.toml, usr/libexec/mios/mios-os-recipe
// AI-functions: createStrictSchema, validateOpenAITool, formatAIHeaderMetadata

/**
 * Strict JSON Schema primitive types supported by OpenAI Function Calling and Structured Outputs.
 */
export type JSONSchemaPrimitive = "string" | "number" | "integer" | "boolean" | "null";

export type JSONSchemaType = JSONSchemaPrimitive | "object" | "array" | JSONSchemaPrimitive[];

/**
 * Strict OpenAI JSON Schema property node.
 */
export interface StrictSchemaProperty {
  type: JSONSchemaType;
  description?: string;
  enum?: string[];
  items?: StrictSchemaProperty;
  properties?: Record<string, StrictSchemaProperty>;
  required?: string[];
  additionalProperties?: false;
}

/**
 * Strict OpenAI Root Object Schema.
 */
export interface StrictObjectSchema {
  type: "object";
  properties: Record<string, StrictSchemaProperty>;
  required: string[];
  additionalProperties: false;
  description?: string;
}

/**
 * OpenAI-compatible Tool Definition with Strict Schema enforcement.
 */
export interface OpenAITool {
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: StrictObjectSchema;
    strict: true;
  };
}

/**
 * OpenAI-compatible Structured Outputs Response Format (Responses API / Chat Completions).
 */
export interface OpenAIResponseFormat {
  type: "json_schema";
  json_schema: {
    name: string;
    description?: string;
    strict: true;
    schema: StrictObjectSchema;
  };
}

/**
 * First-class Native AI Header Metadata parsed from source files and units.
 */
export interface AIHeaderMetadata {
  path: string;
  hint: string | null;
  related: string[];
  functions: string[];
  doc: string | null;
  comment_style: "hash" | "slash" | "xml" | "semi" | "dash";
  has_shebang: boolean;
}

/**
 * Safe OS Recipe Definition mapped from mios.toml [recipes.*].
 */
export interface RecipeDefinition {
  name: string;
  template: string;
  args: string[];
  wsl_paths?: string[];
  description?: string;
  timeout_seconds?: number;
}

/**
 * Execution Result emitted by usr/libexec/mios/mios-os-recipe.
 */
export interface RecipeExecutionResult {
  success: boolean;
  recipe: string;
  target_os: "linux" | "windows";
  template: string;
  exit_code: number;
  stdout: string;
  stderr: string;
}

/**
 * Linux Native Keyring / Freedesktop Secret Service descriptor.
 */
export interface LinuxKeyringSecret {
  schema_name: string;
  label: string;
  attributes: Record<string, string>;
  secret_bytes: string;
  collection?: "default" | "session" | "login";
}

/**
 * Blink Shell iOS Keyboard Mapping & SmartBar Shortcut Descriptor.
 */
export interface BlinkShellKeyCast {
  key: string;
  modifiers: ("shift" | "ctrl" | "alt" | "cmd")[];
  action: "sendSequence" | "runCommand";
  value: string;
  smart_bar_label?: string;
}

/**
 * Converts a partial schema into a fully-compliant strict OpenAI object schema.
 */
export function createStrictSchema(
  properties: Record<string, StrictSchemaProperty>,
  description?: string
): StrictObjectSchema {
  return {
    type: "object",
    properties,
    required: Object.keys(properties),
    additionalProperties: false,
    description,
  };
}

/**
 * Validates that an OpenAITool strictly complies with OpenAI API constraints.
 */
export function validateOpenAITool(tool: OpenAITool): boolean {
  if (tool.type !== "function") return false;
  if (!tool.function || !tool.function.name) return false;
  if (tool.function.strict !== true) return false;
  const params = tool.function.parameters;
  if (params.type !== "object" || params.additionalProperties !== false) return false;
  return Array.isArray(params.required);
}

/**
 * Formats AI metadata into standardized comment headers.
 */
export function formatAIHeaderMetadata(meta: AIHeaderMetadata): string[] {
  const prefix = meta.comment_style === "slash" ? "// " : meta.comment_style === "xml" ? "<!-- " : "# ";
  const suffix = meta.comment_style === "xml" ? " -->" : "";
  const lines: string[] = [];

  if (meta.hint) {
    lines.push(`${prefix}AI-hint: ${meta.hint}${suffix}`);
  }
  if (meta.related.length > 0) {
    lines.push(`${prefix}AI-related: ${meta.related.join(", ")}${suffix}`);
  }
  if (meta.functions.length > 0) {
    lines.push(`${prefix}AI-functions: ${meta.functions.join(", ")}${suffix}`);
  }
  if (meta.doc) {
    lines.push(`${prefix}AI-doc: ${meta.doc}${suffix}`);
  }
  return lines;
}
