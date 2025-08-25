#!/bin/bash

# PathPal Flutter Build Script
# This script handles code generation and build processes for the PathPal Flutter app

set -e  # Exit on any error

echo "🚀 PathPal Flutter Build Script"
echo "==============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Flutter is installed
if ! command -v flutter &> /dev/null; then
    print_error "Flutter is not installed or not in PATH"
    print_error "Please install Flutter from https://flutter.dev/docs/get-started/install"
    exit 1
fi

# Check Flutter version
print_status "Checking Flutter version..."
flutter --version

# Navigate to Flutter project directory
cd "$(dirname "$0")/.."

print_status "Current directory: $(pwd)"

# Clean previous builds
print_status "Cleaning previous builds..."
flutter clean

# Get dependencies
print_status "Getting Flutter dependencies..."
flutter pub get

# Check if build_runner is available
if flutter pub deps | grep -q "build_runner"; then
    print_status "Running code generation with build_runner..."
    
    # Clean previous generated files
    print_status "Cleaning previous generated files..."
    flutter pub run build_runner clean
    
    # Generate code
    print_status "Generating code (Riverpod, Freezed, Retrofit, JSON)..."
    flutter pub run build_runner build --delete-conflicting-outputs
    
    # Check if generation was successful
    if [ $? -eq 0 ]; then
        print_success "Code generation completed successfully!"
    else
        print_error "Code generation failed!"
        exit 1
    fi
else
    print_warning "build_runner not found in dependencies"
    print_warning "Skipping code generation step"
fi

# Run static analysis
print_status "Running Flutter analyze..."
if flutter analyze; then
    print_success "Static analysis passed!"
else
    print_warning "Static analysis found issues. Please review the output above."
fi

# Check code formatting
print_status "Checking code formatting..."
if dart format --set-exit-if-changed lib/ test/; then
    print_success "Code formatting is correct!"
else
    print_warning "Code formatting issues found. Run 'dart format lib/ test/' to fix them."
fi

# Run custom lint if available
if flutter pub deps | grep -q "custom_lint"; then
    print_status "Running custom lint checks..."
    if flutter pub run custom_lint; then
        print_success "Custom lint checks passed!"
    else
        print_warning "Custom lint found issues. Please review the output above."
    fi
fi

# Run tests
print_status "Running Flutter tests..."
if flutter test; then
    print_success "All tests passed!"
else
    print_error "Some tests failed!"
    exit 1
fi

# Build for different targets
BUILD_TARGET=${1:-debug}

case $BUILD_TARGET in
    debug|Debug)
        print_status "Building debug APK..."
        flutter build apk --debug
        print_success "Debug APK built successfully!"
        ;;
    profile|Profile)
        print_status "Building profile APK..."
        flutter build apk --profile
        print_success "Profile APK built successfully!"
        ;;
    release|Release)
        print_status "Building release APK..."
        flutter build apk --release
        print_success "Release APK built successfully!"
        ;;
    ios|iOS)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            print_status "Building iOS app..."
            flutter build ios --release --no-codesign
            print_success "iOS app built successfully!"
        else
            print_warning "iOS build is only supported on macOS"
        fi
        ;;
    all|All)
        print_status "Building all targets..."
        flutter build apk --debug
        flutter build apk --profile
        flutter build apk --release
        if [[ "$OSTYPE" == "darwin"* ]]; then
            flutter build ios --release --no-codesign
        fi
        print_success "All builds completed successfully!"
        ;;
    *)
        print_status "Building default debug APK..."
        flutter build apk --debug
        print_success "Debug APK built successfully!"
        ;;
esac

print_success "🎉 Build script completed successfully!"
print_status "Generated files location:"
print_status "  - Android APK: build/app/outputs/flutter-apk/"
if [[ "$OSTYPE" == "darwin"* ]] && [[ "$BUILD_TARGET" == "ios" || "$BUILD_TARGET" == "all" ]]; then
    print_status "  - iOS App: build/ios/iphoneos/Runner.app"
fi

echo ""
print_status "Next steps:"
print_status "  1. Test the built app on a device or emulator"
print_status "  2. Run 'flutter run' for development"
print_status "  3. Run 'flutter run --release' for release testing"
echo ""

exit 0