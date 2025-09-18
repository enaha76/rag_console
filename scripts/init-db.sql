-- Initialize RAG Console Database
-- This script sets up the basic database configuration

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema for the application
CREATE SCHEMA IF NOT EXISTS rag_console;

-- Set default search path
SET search_path TO rag_console, public;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA rag_console TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA rag_console TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA rag_console TO postgres;