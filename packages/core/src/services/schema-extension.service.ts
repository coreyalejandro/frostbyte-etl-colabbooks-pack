import Ajv from 'ajv';
import addFormats from 'ajv-formats';

interface CustomField {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'date' | 'array' | 'object';
  required?: boolean;
  description?: string;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    enum?: string[];
  };
}

interface TenantSchema {
  tenant_id: string;
  schema_version?: string;
  fields: CustomField[];
}

interface ValidationResult {
  valid: boolean;
  errors?: string[];
}

export class SchemaExtensionService {
  private ajv: Ajv;
  private schemaValidator: ReturnType<Ajv['compile']>;

  constructor() {
    this.ajv = new Ajv({ strict: true, allErrors: true });
    addFormats(this.ajv);
    
    // Load and compile the tenant custom schema
    const schema = require('../../schemas/tenant-custom-schema.json');
    this.schemaValidator = this.ajv.compile(schema);
  }

  /**
   * Validate a tenant's custom schema definition
   */
  validateSchemaDefinition(schema: TenantSchema): ValidationResult {
    const valid = this.schemaValidator(schema);
    
    if (!valid && this.schemaValidator.errors) {
      return {
        valid: false,
        errors: this.schemaValidator.errors.map(e => 
          `${e.instancePath || 'root'}: ${e.message}`
        )
      };
    }

    // Additional validation: check for duplicate field names
    const fieldNames = schema.fields.map(f => f.name);
    const duplicates = fieldNames.filter((item, index) => fieldNames.indexOf(item) !== index);
    
    if (duplicates.length > 0) {
      return {
        valid: false,
        errors: [`Duplicate field names: ${duplicates.join(', ')}`]
      };
    }

    return { valid: true };
  }

  /**
   * Validate custom metadata against a tenant's schema
   */
  validateMetadata(metadata: Record<string, unknown>, schema: TenantSchema): ValidationResult {
    const errors: string[] = [];

    for (const field of schema.fields) {
      const value = metadata[field.name];

      // Check required fields
      if (field.required && (value === undefined || value === null)) {
        errors.push(`Required field '${field.name}' is missing`);
        continue;
      }

      // Skip validation if value is not provided and not required
      if (value === undefined || value === null) {
        continue;
      }

      // Type validation
      const typeError = this.validateType(value, field);
      if (typeError) {
        errors.push(`Field '${field.name}': ${typeError}`);
        continue;
      }

      // Field-level validation rules
      if (field.validation) {
        const validationError = this.validateFieldConstraints(value, field);
        if (validationError) {
          errors.push(`Field '${field.name}': ${validationError}`);
        }
      }
    }

    // Check for unknown fields
    const allowedFields = new Set(schema.fields.map(f => f.name));
    const unknownFields = Object.keys(metadata).filter(k => !allowedFields.has(k));
    if (unknownFields.length > 0) {
      errors.push(`Unknown fields: ${unknownFields.join(', ')}`);
    }

    return errors.length === 0 ? { valid: true } : { valid: false, errors };
  }

  private validateType(value: unknown, field: CustomField): string | null {
    const jsType = typeof value;
    
    switch (field.type) {
      case 'string':
        if (jsType !== 'string') return `Expected string, got ${jsType}`;
        break;
      case 'number':
        if (jsType !== 'number') return `Expected number, got ${jsType}`;
        break;
      case 'boolean':
        if (jsType !== 'boolean') return `Expected boolean, got ${jsType}`;
        break;
      case 'date':
        if (!(value instanceof Date) && !(typeof value === 'string' && !isNaN(Date.parse(value as string)))) {
          return `Expected valid date, got ${jsType}`;
        }
        break;
      case 'array':
        if (!Array.isArray(value)) return `Expected array, got ${jsType}`;
        break;
      case 'object':
        if (jsType !== 'object' || value === null || Array.isArray(value)) {
          return `Expected object, got ${jsType}`;
        }
        break;
    }
    return null;
  }

  private validateFieldConstraints(value: unknown, field: CustomField): string | null {
    if (!field.validation) return null;

    const { min, max, pattern, enum: enumValues } = field.validation;

    if (field.type === 'string' && typeof value === 'string') {
      if (pattern && !new RegExp(pattern).test(value)) {
        return `Value does not match pattern: ${pattern}`;
      }
      if (enumValues && !enumValues.includes(value)) {
        return `Value must be one of: ${enumValues.join(', ')}`;
      }
    }

    if (field.type === 'number' && typeof value === 'number') {
      if (min !== undefined && value < min) {
        return `Value must be >= ${min}`;
      }
      if (max !== undefined && value > max) {
        return `Value must be <= ${max}`;
      }
    }

    if (field.type === 'array' && Array.isArray(value)) {
      if (min !== undefined && value.length < min) {
        return `Array must have at least ${min} items`;
      }
      if (max !== undefined && value.length > max) {
        return `Array must have at most ${max} items`;
      }
    }

    return null;
  }

  /**
   * Generate JSON Schema for a tenant's custom fields
   */
  generateJsonSchema(schema: TenantSchema): object {
    const properties: Record<string, object> = {};
    const required: string[] = [];

    for (const field of schema.fields) {
      let fieldSchema: Record<string, unknown> = {
        type: field.type === 'date' ? 'string' : field.type,
        description: field.description || undefined
      };

      if (field.type === 'date') {
        fieldSchema.format = 'date-time';
      }

      if (field.validation) {
        if (field.validation.min !== undefined) fieldSchema.minimum = field.validation.min;
        if (field.validation.max !== undefined) fieldSchema.maximum = field.validation.max;
        if (field.validation.pattern) fieldSchema.pattern = field.validation.pattern;
        if (field.validation.enum) fieldSchema.enum = field.validation.enum;
      }

      properties[field.name] = fieldSchema;

      if (field.required) {
        required.push(field.name);
      }
    }

    return {
      type: 'object',
      properties,
      required: required.length > 0 ? required : undefined,
      additionalProperties: false
    };
  }
}

export default SchemaExtensionService;
