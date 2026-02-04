# =============================================================================
# Terraform - Hesperides Trading System IaC
# Despliega en AWS EC2 con Docker pre-instalado
# =============================================================================
#
# Uso:
#   1. Configurar credenciales AWS: aws configure
#   2. terraform init
#   3. terraform plan
#   4. terraform apply
#   5. terraform destroy (para eliminar)
#
# =============================================================================

terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# --- VARIABLES ---
variable "aws_region" {
  description = "Región de AWS"
  default     = "eu-west-1"  # Irlanda (más cercano a España)
}

variable "instance_type" {
  description = "Tipo de instancia EC2"
  default     = "t3.medium"  # 2 vCPU, 4GB RAM - suficiente para el proyecto
}

variable "key_name" {
  description = "Nombre del key pair en AWS para SSH"
  default     = "hesperides-key"
}

# --- PROVIDER ---
provider "aws" {
  region = var.aws_region
}

# --- DATA SOURCES ---
# Obtener la AMI más reciente de Amazon Linux 2023
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# --- SECURITY GROUP ---
resource "aws_security_group" "hesperides_sg" {
  name        = "hesperides-trading-sg"
  description = "Security group para Hesperides Trading System"

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  # Frontend (Nginx)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP Frontend"
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Frontend dev port"
  }

  # API Backend
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "FastAPI Backend"
  }

  # PostgreSQL (solo para debug, en prod cerrar)
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "PostgreSQL"
  }

  # Egress - permitir todo
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "hesperides-sg"
    Project = "Hesperides Trading"
  }
}

# --- EC2 INSTANCE ---
resource "aws_instance" "hesperides_server" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.hesperides_sg.id]

  # Root volume
  root_block_device {
    volume_size = 30  # GB
    volume_type = "gp3"
  }

  # User data - Script de inicialización
  user_data = <<-EOF
    #!/bin/bash
    set -e
    
    # Actualizar sistema
    yum update -y
    
    # Instalar Docker
    yum install -y docker git
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ec2-user
    
    # Instalar Docker Compose v2
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    
    # Clonar repositorio
    cd /home/ec2-user
    git clone https://github.com/nachoddiaz/hesperides-intro-python-Diaz-Ignacio.git app
    chown -R ec2-user:ec2-user app
    
    # Iniciar servicios
    cd app
    docker compose up -d
    
    echo "Hesperides Trading System deployed successfully!"
  EOF

  tags = {
    Name        = "hesperides-trading-server"
    Project     = "Hesperides Trading"
    Environment = "production"
  }
}

# --- OUTPUTS ---
output "instance_id" {
  description = "ID de la instancia EC2"
  value       = aws_instance.hesperides_server.id
}

output "public_ip" {
  description = "IP pública del servidor"
  value       = aws_instance.hesperides_server.public_ip
}

output "public_dns" {
  description = "DNS público del servidor"
  value       = aws_instance.hesperides_server.public_dns
}

output "frontend_url" {
  description = "URL del frontend"
  value       = "http://${aws_instance.hesperides_server.public_ip}:3000"
}

output "api_url" {
  description = "URL de la API"
  value       = "http://${aws_instance.hesperides_server.public_ip}:8000/docs"
}

output "ssh_command" {
  description = "Comando para conectar por SSH"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ec2-user@${aws_instance.hesperides_server.public_ip}"
}
