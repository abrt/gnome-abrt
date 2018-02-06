#!/bin/sh

print_help()
{
cat << EOH
Prepares the source tree for configuration

Usage:
  autogen.sh [sydeps [--install]]

Options:

  sysdeps          prints out all dependencies
    --install      install all dependencies ('sudo yum install \$DEPS')

EOH
}

build_depslist()
{
    PACKAGE=$1
    TEMPFILE=$(mktemp -u --suffix=.spec)
    sed 's/@GNOME_ABRT_VERSION@/1/' < $PACKAGE.spec.in | sed 's/@.*@//' > $TEMPFILE
    rpmspec -P $TEMPFILE | grep "^\(Build\)\?Requires:" | \
        tr -s " " | tr "," "\n" | cut -f2- -d " " | \
        grep -v "^"$PACKAGE | sort -u | sed -E 's/^(.*) (.*)$/"\1 \2"/' | tr \" \'
    rm $TEMPFILE
}

case "$1" in
    "--help"|"-h")
            print_help
            exit 0
        ;;
    "sysdeps")
            DEPS_LIST=$(build_depslist gnome-abrt)

            if [ "$2" == "--install" ]; then
                set -x verbose
                eval sudo dnf install --setopt=strict=0 $DEPS_LIST
                set +x verbose
            else
                echo $DEPS_LIST
            fi
            exit 0
        ;;
    *)
            echo "Running gen-version"
            VN=$(./gen-version | head -1)
            echo -n "$VN" > gnome-abrt-version

            mkdir -p m4
            echo "Creating m4/aclocal.m4 ..."
            test -r m4/aclocal.m4 || touch m4/aclocal.m4

            echo "Running autopoint"
            autopoint --force || exit 1

            echo "Running intltoolize..."
            intltoolize --force --copy --automake || exit 1

            echo "Running aclocal..."
            aclocal || exit 1

            echo "Running libtoolize..."
            libtoolize || exit 1

            echo "Running autoconf..."
            autoconf --force || exit 1

            echo "Running automake..."
            automake --add-missing --force --copy || exit 1

            echo "Running configure ..."
            ./configure "$@"
        ;;
esac
