import Fastify from 'fastify';
import swagger from '@fastify/swagger';
import cors from '@fastify/cors';
import { writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';

const fastify = Fastify({ logger: false });

async function generateOpenApi() {
  // Register CORS
  await fastify.register(cors, { origin: true });

  // Register Swagger
  await fastify.register(swagger, {
    openapi: {
      info: {
        title: 'Frostbyte API',
        version: '1.0.0',
        description: 'Multi-tenant ETL pipeline API'
      },
      servers: [
        { url: 'http://localhost:3000', description: 'Development server' }
      ]
    }
  });

  // Health check route
  fastify.get('/health', {
    schema: {
      description: 'Health check endpoint',
      tags: ['system'],
      response: {
        200: {
          type: 'object',
          properties: {
            status: { type: 'string' },
            timestamp: { type: 'string' }
          }
        }
      }
    }
  }, async () => ({ status: 'healthy', timestamp: new Date().toISOString() }));

  // API status route
  fastify.get('/api/v1/status', {
    schema: {
      description: 'Get API status',
      tags: ['system'],
      response: {
        200: {
          type: 'object',
          properties: {
            version: { type: 'string' },
            uptime: { type: 'number' }
          }
        }
      }
    }
  }, async () => ({ version: '1.0.0', uptime: 0 }));

  // Trigger swagger generation
  await fastify.ready();

  // Get the OpenAPI spec
  const spec = fastify.swagger();

  // Ensure docs directory exists
  const docsDir = join(process.cwd(), '..', '..', 'docs', 'api');
  mkdirSync(docsDir, { recursive: true });

  // Write the spec
  const specPath = join(docsDir, 'openapi.yaml');
  writeFileSync(specPath, JSON.stringify(spec, null, 2));

  console.log(`OpenAPI spec generated: ${specPath}`);
  process.exit(0);
}

generateOpenApi().catch(err => {
  console.error(err);
  process.exit(1);
});
