import Fastify from 'fastify';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import cors from '@fastify/cors';
import schemaRoutes from './routes/schema.routes';

const fastify = Fastify({
  logger: true
});

async function main() {
  // Register CORS
  await fastify.register(cors, {
    origin: true
  });

  // Register Swagger
  await fastify.register(swagger, {
    openapi: {
      info: {
        title: 'Frostbyte API',
        version: '1.0.0',
        description: 'Multi-tenant ETL pipeline API'
      },
      servers: [
        {
          url: 'http://localhost:3000',
          description: 'Development server'
        }
      ],
      tags: [
        { name: 'system', description: 'System endpoints' },
        { name: 'schema', description: 'Custom schema management' }
      ]
    }
  });

  // Register Swagger UI
  await fastify.register(swaggerUi, {
    routePrefix: '/docs',
    uiConfig: {
      docExpansion: 'full',
      deepLinking: false
    }
  });

  // Register schema routes
  await fastify.register(schemaRoutes, { prefix: '/api/v1' });

  // Health check route with schema
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
  }, async () => {
    return {
      status: 'healthy',
      timestamp: new Date().toISOString()
    };
  });

  // Example API route with schema
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
  }, async () => {
    return {
      version: '1.0.0',
      uptime: process.uptime()
    };
  });

  try {
    await fastify.listen({ port: 3000, host: '0.0.0.0' });
    fastify.log.info('Server listening on port 3000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
}

main();
