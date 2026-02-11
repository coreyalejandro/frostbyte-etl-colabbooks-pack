import { FastifyInstance } from 'fastify';
import SchemaExtensionService from '../../core/src/services/schema-extension.service';

const schemaService = new SchemaExtensionService();

// In-memory storage for tenant schemas (replace with database in production)
const tenantSchemas = new Map<string, any>();

export async function schemaRoutes(fastify: FastifyInstance) {
  // Get tenant schema
  fastify.get('/schema', {
    schema: {
      description: 'Get tenant custom schema definition',
      tags: ['schema'],
      response: {
        200: {
          type: 'object',
          properties: {
            tenant_id: { type: 'string' },
            schema_version: { type: 'string' },
            fields: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  name: { type: 'string' },
                  type: { type: 'string' },
                  required: { type: 'boolean' },
                  description: { type: 'string' }
                }
              }
            }
          }
        },
        404: {
          type: 'object',
          properties: {
            error: { type: 'string' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const tenantId = request.headers['x-tenant-id'] as string || 'default';
    const schema = tenantSchemas.get(tenantId);
    
    if (!schema) {
      return reply.status(404).send({ error: 'No custom schema defined for tenant' });
    }
    
    return schema;
  });

  // Create or update tenant schema
  fastify.post('/schema', {
    schema: {
      description: 'Define custom schema for tenant',
      tags: ['schema'],
      body: {
        type: 'object',
        properties: {
          schema_version: { type: 'string' },
          fields: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                name: { type: 'string' },
                type: { type: 'string', enum: ['string', 'number', 'boolean', 'date', 'array', 'object'] },
                required: { type: 'boolean' },
                description: { type: 'string' },
                validation: { type: 'object' }
              },
              required: ['name', 'type']
            }
          }
        },
        required: ['fields']
      },
      response: {
        201: {
          type: 'object',
          properties: {
            message: { type: 'string' },
            tenant_id: { type: 'string' },
            field_count: { type: 'number' }
          }
        },
        400: {
          type: 'object',
          properties: {
            error: { type: 'string' },
            details: { type: 'array', items: { type: 'string' } }
          }
        }
      }
    }
  }, async (request, reply) => {
    const tenantId = request.headers['x-tenant-id'] as string || 'default';
    const body = request.body as any;
    
    const schema = {
      tenant_id: tenantId,
      schema_version: body.schema_version || '1.0',
      fields: body.fields
    };
    
    // Validate schema definition
    const validation = schemaService.validateSchemaDefinition(schema);
    if (!validation.valid) {
      return reply.status(400).send({
        error: 'Invalid schema definition',
        details: validation.errors
      });
    }
    
    // Store schema
    tenantSchemas.set(tenantId, schema);
    
    return reply.status(201).send({
      message: 'Schema created successfully',
      tenant_id: tenantId,
      field_count: schema.fields.length
    });
  });

  // Validate metadata against schema
  fastify.post('/schema/validate', {
    schema: {
      description: 'Validate custom metadata against tenant schema',
      tags: ['schema'],
      body: {
        type: 'object',
        properties: {
          metadata: { type: 'object' }
        },
        required: ['metadata']
      },
      response: {
        200: {
          type: 'object',
          properties: {
            valid: { type: 'boolean' },
            errors: { type: 'array', items: { type: 'string' } }
          }
        },
        404: {
          type: 'object',
          properties: {
            error: { type: 'string' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const tenantId = request.headers['x-tenant-id'] as string || 'default';
    const { metadata } = request.body as { metadata: Record<string, unknown> };
    
    const schema = tenantSchemas.get(tenantId);
    if (!schema) {
      return reply.status(404).send({ error: 'No custom schema defined for tenant' });
    }
    
    const validation = schemaService.validateMetadata(metadata, schema);
    
    return {
      valid: validation.valid,
      errors: validation.errors || []
    };
  });

  // Delete tenant schema
  fastify.delete('/schema', {
    schema: {
      description: 'Delete tenant custom schema',
      tags: ['schema'],
      response: {
        200: {
          type: 'object',
          properties: {
            message: { type: 'string' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const tenantId = request.headers['x-tenant-id'] as string || 'default';
    tenantSchemas.delete(tenantId);
    
    return { message: 'Schema deleted successfully' };
  });
}

export default schemaRoutes;
