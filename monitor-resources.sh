#!/bin/bash

# monitor-resources.sh - Container Resource Monitoring Script
# This script helps monitor Docker container resource usage and compare against limits

set -e

COMPOSE_FILE="docker-compose.prod.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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
    echo -e "${CYAN}ℹ $1${NC}"
}

# --- Resource Monitoring Functions ---

get_container_stats() {
    # Get real-time stats for all containers
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
}

get_detailed_stats() {
    # Get detailed stats for each container
    local containers=$(docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null)

    if [ -z "$containers" ]; then
        print_error "No running containers found"
        return 1
    fi

    echo -e "${BLUE}Container Resource Usage:${NC}"
    echo

    for container_id in $containers; do
        local name=$(docker inspect --format='{{.Name}}' "$container_id" | sed 's/\///')
        local cpu=$(docker stats --no-stream --format "{{.CPUPerc}}" "$container_id")
        local mem=$(docker stats --no-stream --format "{{.MemUsage}}" "$container_id")
        local mem_perc=$(docker stats --no-stream --format "{{.MemPerc}}" "$container_id")

        echo -e "${CYAN}$name${NC}"
        echo "  CPU:    $cpu"
        echo "  Memory: $mem ($mem_perc)"
        echo
    done
}

check_resource_limits() {
    print_header "Resource Limits Check"

    local containers=$(docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null)

    if [ -z "$containers" ]; then
        print_error "No running containers found"
        return 1
    fi

    for container_id in $containers; do
        local name=$(docker inspect --format='{{.Name}}' "$container_id" | sed 's/\///')

        # Get resource limits
        local cpu_limit=$(docker inspect --format='{{.HostConfig.NanoCpus}}' "$container_id")
        local mem_limit=$(docker inspect --format='{{.HostConfig.Memory}}' "$container_id")

        # Get current usage
        local cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" "$container_id" | sed 's/%//')
        local mem_usage=$(docker stats --no-stream --format "{{.MemPerc}}" "$container_id" | sed 's/%//')

        echo -e "${CYAN}$name${NC}"

        # Check CPU limit
        if [ "$cpu_limit" = "0" ]; then
            print_warning "  CPU: No limit set (unlimited)"
        else
            local cpu_cores=$(echo "scale=2; $cpu_limit / 1000000000" | bc)
            echo -e "  CPU Limit: ${GREEN}${cpu_cores} cores${NC}"
        fi

        # Check Memory limit
        if [ "$mem_limit" = "0" ]; then
            print_warning "  Memory: No limit set (unlimited)"
        else
            local mem_mb=$(echo "scale=0; $mem_limit / 1048576" | bc)
            echo -e "  Memory Limit: ${GREEN}${mem_mb}MB${NC}"
        fi

        # Check if approaching limits
        if [ "$mem_limit" != "0" ]; then
            if (( $(echo "$mem_usage > 80" | bc -l) )); then
                print_warning "  Memory usage is high (${mem_usage}%)"
            elif (( $(echo "$mem_usage > 60" | bc -l) )); then
                print_info "  Memory usage: ${mem_usage}%"
            else
                print_success "  Memory usage: ${mem_usage}%"
            fi
        fi

        echo
    done
}

continuous_monitor() {
    local interval=${1:-5}

    print_header "Continuous Resource Monitoring (Ctrl+C to stop)"
    print_info "Update interval: ${interval} seconds"
    echo

    while true; do
        clear
        echo -e "${BLUE}OneSpirit Resource Monitor - $(date)${NC}"
        echo
        get_container_stats
        echo
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        sleep "$interval"
    done
}

export_stats() {
    local output_file="resource-stats-$(date +%Y%m%d_%H%M%S).csv"

    print_info "Exporting resource statistics to ${output_file}..."

    echo "Timestamp,Container,CPU%,Memory,MemPerc,NetIO,BlockIO" > "$output_file"

    local containers=$(docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null)

    for container_id in $containers; do
        local name=$(docker inspect --format='{{.Name}}' "$container_id" | sed 's/\///')
        local stats=$(docker stats --no-stream --format "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}}" "$container_id")
        echo "$(date +%Y-%m-%d\ %H:%M:%S),$name,$stats" >> "$output_file"
    done

    print_success "Statistics exported to ${output_file}"
}

show_top_consumers() {
    print_header "Top Resource Consumers"

    echo -e "${CYAN}Top CPU Consumers:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}" | sort -k2 -rh | head -6

    echo
    echo -e "${CYAN}Top Memory Consumers:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}" | sort -k3 -rh | head -6
}

check_system_resources() {
    print_header "System Resources"

    # Check available system resources
    echo -e "${CYAN}CPU Information:${NC}"
    lscpu | grep -E "^CPU\(s\)|^Model name|^CPU MHz"

    echo
    echo -e "${CYAN}Memory Information:${NC}"
    free -h

    echo
    echo -e "${CYAN}Disk Usage:${NC}"
    df -h / | tail -1

    echo
    echo -e "${CYAN}Docker Disk Usage:${NC}"
    docker system df
}

recommend_limits() {
    print_header "Resource Limit Recommendations"

    print_info "Analyzing current usage patterns..."
    echo

    local containers=$(docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null)

    for container_id in $containers; do
        local name=$(docker inspect --format='{{.Name}}' "$container_id" | sed 's/\///')

        # Get current usage
        local cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" "$container_id" | sed 's/%//')
        local mem_usage_raw=$(docker stats --no-stream --format "{{.MemUsage}}" "$container_id" | awk '{print $1}')
        local mem_unit=$(docker stats --no-stream --format "{{.MemUsage}}" "$container_id" | awk '{print $2}')

        echo -e "${CYAN}$name${NC}"

        # Convert memory to MB for calculation
        local mem_mb=0
        if [[ $mem_unit == *"GiB"* ]]; then
            mem_mb=$(echo "$mem_usage_raw * 1024" | bc | cut -d'.' -f1)
        else
            mem_mb=$(echo "$mem_usage_raw" | cut -d'.' -f1)
        fi

        # Recommend limits (2x current usage + buffer)
        local recommended_cpu=$(echo "scale=1; $cpu_usage * 2 / 100 + 0.5" | bc)
        local recommended_mem=$(echo "$mem_mb * 2 + 256" | bc | cut -d'.' -f1)

        echo "  Current CPU: ${cpu_usage}%"
        echo "  Current Memory: ${mem_usage_raw}${mem_unit}"
        echo
        echo -e "  ${GREEN}Recommended Limits:${NC}"
        echo "    CPU: ${recommended_cpu} cores"
        echo "    Memory: ${recommended_mem}MB"
        echo
    done

    print_warning "Note: These are baseline recommendations. Adjust based on peak load patterns."
}

show_help() {
    echo "Usage: ./monitor-resources.sh [COMMAND] [OPTIONS]"
    echo
    echo "Container Resource Monitoring for OneSpirit"
    echo
    echo "Commands:"
    echo "  stats               Show current resource statistics (default)"
    echo "  check               Check resource limits configuration"
    echo "  monitor [interval]  Continuous monitoring (default: 5s)"
    echo "  top                 Show top resource consumers"
    echo "  system              Show system resource information"
    echo "  export              Export statistics to CSV file"
    echo "  recommend           Analyze usage and recommend limits"
    echo "  help                Show this help message"
    echo
    echo "Examples:"
    echo "  ./monitor-resources.sh stats          # Quick stats view"
    echo "  ./monitor-resources.sh check          # Check configured limits"
    echo "  ./monitor-resources.sh monitor 10     # Monitor every 10 seconds"
    echo "  ./monitor-resources.sh top            # Show top consumers"
    echo "  ./monitor-resources.sh recommend      # Get limit recommendations"
    echo
}

# --- Main Execution ---

COMMAND=${1:-stats}

case $COMMAND in
    stats)
        print_header "Container Resource Statistics"
        get_detailed_stats
        ;;
    check)
        check_resource_limits
        ;;
    monitor)
        shift
        continuous_monitor "$@"
        ;;
    top)
        show_top_consumers
        ;;
    system)
        check_system_resources
        ;;
    export)
        export_stats
        ;;
    recommend)
        recommend_limits
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo
        show_help
        exit 1
        ;;
esac
