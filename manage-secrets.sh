#!/bin/bash

# manage-secrets.sh - Docker Secrets Management Script
# This script helps create, validate, and manage Docker secrets for OneSpirit

set -e

SECRETS_DIR="secrets"
REQUIRED_SECRETS=("db_password" "django_secret_key" "redis_password")
OPTIONAL_SECRETS=("email_password" "aws_secret_access_key" "sentry_dsn")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Utility Functions ---

print_header() {
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}==================================================${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# --- Secret Generation Functions ---

generate_django_secret() {
    python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key(), end="")'
}

generate_random_password() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d '\n'
}

generate_hex_secret() {
    local length=${1:-32}
    openssl rand -hex $length | tr -d '\n'
}

# --- Secret File Functions ---

create_secret_file() {
    local secret_name=$1
    local secret_value=$2
    local file_path="${SECRETS_DIR}/${secret_name}.txt"

    echo -n "$secret_value" > "$file_path"
    chmod 600 "$file_path"
    print_success "Created ${file_path}"
}

check_secret_exists() {
    local secret_name=$1
    local file_path="${SECRETS_DIR}/${secret_name}.txt"

    if [ -f "$file_path" ]; then
        return 0
    else
        return 1
    fi
}

validate_secret_file() {
    local secret_name=$1
    local file_path="${SECRETS_DIR}/${secret_name}.txt"

    if [ ! -f "$file_path" ]; then
        print_error "${secret_name}: File not found"
        return 1
    fi

    # Check file is not empty
    if [ ! -s "$file_path" ]; then
        print_error "${secret_name}: File is empty"
        return 1
    fi

    # Check permissions
    local perms=$(stat -c %a "$file_path" 2>/dev/null || stat -f %A "$file_path" 2>/dev/null)
    if [ "$perms" != "600" ]; then
        print_warning "${secret_name}: Permissions are $perms (should be 600)"
        print_info "  Run: chmod 600 ${file_path}"
    fi

    # Check for newlines (common mistake)
    if grep -q $'\n' "$file_path"; then
        print_warning "${secret_name}: Contains newline characters (may cause issues)"
    fi

    local size=$(wc -c < "$file_path" | tr -d ' ')
    print_success "${secret_name}: Valid (${size} bytes)"
    return 0
}

# --- Command Functions ---

cmd_init() {
    print_header "Initialize Docker Secrets"

    # Create secrets directory if it doesn't exist
    if [ ! -d "$SECRETS_DIR" ]; then
        mkdir -p "$SECRETS_DIR"
        print_success "Created ${SECRETS_DIR}/ directory"
    fi

    echo
    print_info "This will guide you through creating required secrets."
    print_info "You can provide your own values or let the script generate them."
    echo

    # Process required secrets
    for secret_name in "${REQUIRED_SECRETS[@]}"; do
        if check_secret_exists "$secret_name"; then
            echo -e "${YELLOW}Secret '${secret_name}' already exists.${NC}"
            read -p "Overwrite? (yes/no): " overwrite
            if [ "$overwrite" != "yes" ]; then
                print_info "Skipping ${secret_name}"
                echo
                continue
            fi
        fi

        echo
        echo -e "${BLUE}Creating secret: ${secret_name}${NC}"
        read -p "Enter value (or press Enter to auto-generate): " value

        if [ -z "$value" ]; then
            case $secret_name in
                django_secret_key)
                    value=$(generate_django_secret)
                    print_info "Generated Django secret key"
                    ;;
                db_password)
                    value=$(generate_random_password 32)
                    print_info "Generated random password (32 chars)"
                    ;;
                *)
                    value=$(generate_hex_secret 32)
                    print_info "Generated random hex secret"
                    ;;
            esac
        fi

        create_secret_file "$secret_name" "$value"
        echo
    done

    # Process optional secrets
    echo
    print_info "Optional secrets (press Enter to skip):"
    echo

    for secret_name in "${OPTIONAL_SECRETS[@]}"; do
        if check_secret_exists "$secret_name"; then
            print_info "${secret_name}: Already exists (skipping)"
            continue
        fi

        read -p "Create '${secret_name}'? (yes/no): " create
        if [ "$create" = "yes" ]; then
            read -p "Enter value: " value
            if [ -n "$value" ]; then
                create_secret_file "$secret_name" "$value"
            fi
        fi
        echo
    done

    echo
    print_success "Secrets initialization complete!"
    echo
    print_info "Next steps:"
    echo "  1. Review secrets with: ./manage-secrets.sh list"
    echo "  2. Validate secrets with: ./manage-secrets.sh validate"
    echo "  3. Deploy with: ./setup-prod.sh init"
}

cmd_list() {
    print_header "Docker Secrets Status"

    if [ ! -d "$SECRETS_DIR" ]; then
        print_error "Secrets directory not found: ${SECRETS_DIR}"
        exit 1
    fi

    echo -e "${BLUE}Required Secrets:${NC}"
    for secret_name in "${REQUIRED_SECRETS[@]}"; do
        if check_secret_exists "$secret_name"; then
            local size=$(wc -c < "${SECRETS_DIR}/${secret_name}.txt" | tr -d ' ')
            echo -e "  ${GREEN}✓${NC} ${secret_name} (${size} bytes)"
        else
            echo -e "  ${RED}✗${NC} ${secret_name} ${RED}[MISSING]${NC}"
        fi
    done

    echo
    echo -e "${BLUE}Optional Secrets:${NC}"
    for secret_name in "${OPTIONAL_SECRETS[@]}"; do
        if check_secret_exists "$secret_name"; then
            local size=$(wc -c < "${SECRETS_DIR}/${secret_name}.txt" | tr -d ' ')
            echo -e "  ${GREEN}✓${NC} ${secret_name} (${size} bytes)"
        else
            echo -e "  ${YELLOW}○${NC} ${secret_name} (not configured)"
        fi
    done

    echo
}

cmd_validate() {
    print_header "Validate Docker Secrets"

    local errors=0

    echo "Checking required secrets..."
    echo
    for secret_name in "${REQUIRED_SECRETS[@]}"; do
        if ! validate_secret_file "$secret_name"; then
            ((errors++))
        fi
    done

    echo
    echo "Checking optional secrets..."
    echo
    for secret_name in "${OPTIONAL_SECRETS[@]}"; do
        if check_secret_exists "$secret_name"; then
            if ! validate_secret_file "$secret_name"; then
                ((errors++))
            fi
        else
            print_info "${secret_name}: Not configured (optional)"
        fi
    done

    echo
    if [ $errors -eq 0 ]; then
        print_success "All secrets are valid!"
        return 0
    else
        print_error "Found $errors error(s)"
        return 1
    fi
}

cmd_generate() {
    local secret_name=$1

    if [ -z "$secret_name" ]; then
        print_error "Usage: ./manage-secrets.sh generate <secret_name>"
        echo
        echo "Available generators:"
        echo "  django_secret_key  - Generate Django SECRET_KEY"
        echo "  password           - Generate random password (32 chars)"
        echo "  hex                - Generate hex secret (32 bytes)"
        exit 1
    fi

    case $secret_name in
        django_secret_key)
            generate_django_secret
            ;;
        password)
            generate_random_password 32
            ;;
        hex)
            generate_hex_secret 32
            ;;
        *)
            print_error "Unknown secret type: $secret_name"
            exit 1
            ;;
    esac
    echo  # Add newline at end
}

cmd_rotate() {
    local secret_name=$1

    if [ -z "$secret_name" ]; then
        print_error "Usage: ./manage-secrets.sh rotate <secret_name>"
        exit 1
    fi

    if ! check_secret_exists "$secret_name"; then
        print_error "Secret '${secret_name}' does not exist"
        exit 1
    fi

    print_warning "This will replace the secret '${secret_name}' with a new value!"
    read -p "Continue? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        print_info "Rotation cancelled"
        exit 0
    fi

    # Backup old secret
    local backup_file="${SECRETS_DIR}/${secret_name}.txt.backup.$(date +%Y%m%d_%H%M%S)"
    cp "${SECRETS_DIR}/${secret_name}.txt" "$backup_file"
    print_info "Backed up old secret to: ${backup_file}"

    # Generate new secret
    read -p "Enter new value (or press Enter to auto-generate): " value

    if [ -z "$value" ]; then
        case $secret_name in
            django_secret_key)
                value=$(generate_django_secret)
                ;;
            *)
                value=$(generate_random_password 32)
                ;;
        esac
        print_info "Generated new value"
    fi

    create_secret_file "$secret_name" "$value"

    print_success "Secret rotated successfully!"
    print_warning "Remember to restart services: ./setup-prod.sh restart"
}

cmd_help() {
    echo "Usage: ./manage-secrets.sh [COMMAND]"
    echo
    echo "Docker Secrets Management for OneSpirit"
    echo
    echo "Commands:"
    echo "  init               Initialize secrets (interactive)"
    echo "  list               List all secrets and their status"
    echo "  validate           Validate all secret files"
    echo "  generate <type>    Generate a secret value"
    echo "                     Types: django_secret_key, password, hex"
    echo "  rotate <name>      Rotate (replace) an existing secret"
    echo "  help               Show this help message"
    echo
    echo "Examples:"
    echo "  ./manage-secrets.sh init                    # Interactive setup"
    echo "  ./manage-secrets.sh list                    # Check status"
    echo "  ./manage-secrets.sh validate                # Validate files"
    echo "  ./manage-secrets.sh generate password       # Generate password"
    echo "  ./manage-secrets.sh rotate db_password      # Rotate DB password"
    echo
}

# --- Main Execution ---

COMMAND=$1

case $COMMAND in
    init)
        cmd_init
        ;;
    list)
        cmd_list
        ;;
    validate)
        cmd_validate
        ;;
    generate)
        shift
        cmd_generate "$@"
        ;;
    rotate)
        shift
        cmd_rotate "$@"
        ;;
    help|--help|-h)
        cmd_help
        ;;
    "")
        cmd_help
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo
        cmd_help
        exit 1
        ;;
esac
