%global with_check 0

Name:           containernetworking-plugins
Version:        0.8.2
Release:        3.git485be65
Summary:        Library for use by writing CNI plugin
License:        ASL 2.0
URL:            https://github.com/containernetworking/plugins
Source0:        https://github.com/containernetworking/plugins/archive/485be65581341430f9106a194a98f0f2412245fb.tar.gz

BuildRequires:  compiler(go-compiler) git

Obsoletes:      containernetworking-cni < 0.7.1-2
Provides:       containernetworking-cni = %{version}-%{release} kubernetes-cni

%description
The CNI (Container Network Interface) project consists of a specification and libraries for
writing plugins to configure network interfaces in Linux containers, along with a number of
supported plugins. CNI concerns itself only with network connectivity of containers and removing
allocated resources when the container is deleted.


%package devel
Summary:  Library for use by writing CNI plugin
BuildArch:noarch

%description devel
%{name}-devel provides libraries for those packages with the "github.com/containernetworking/plugins"
prefix to be used at build time.

%package unit-test-devel
Summary: Unit tests for containernetworking-plugins package

Requires: %{name}-devel = %{version}-%{release}

%description unit-test-devel
%{name}-devel provides libraries for those packages with the "github.com/containernetworking/plugins"
prefix to be used at build time.

%prep
%autosetup -Sgit -n plugins-485be65581341430f9106a194a98f0f2412245fb -p1
rm -rf plugins/main/windows

%build
export ORG_PATH="github.com/containernetworking"
export REPO_PATH="github.com/containernetworking/plugins"

if [ ! -h gopath/src/github.com/containernetworking/plugins ]; then
        mkdir -p gopath/src/github.com/containernetworking
        ln -s ../../../.. gopath/src/github.com/containernetworking/plugins || exit 255
fi

export GOPATH=$(pwd)/gopath
mkdir -p $(pwd)/bin
export GO111MODULE=off
export PLUGINS="plugins/meta/* plugins/main/* plugins/ipam/* plugins/sample"

for dirpath in $PLUGINS; do
        if [ -d "$dirpath" ]; then
                plugin="$(basename "$dirpath")"
                %gobuild -o "${PWD}/bin/$plugin" "$@" github.com/containernetworking/plugins/$dirpath
        fi
done

%install
install -d -p     %{buildroot}%{_libexecdir}/cni/
install -p -m755  bin/* %{buildroot}/%{_libexecdir}/cni
install -d -p     %{buildroot}/%{gopath}/src/github.com/containernetworking/plugins/

echo "%%dir %%{gopath}/src/github.com/containernetworking/plugins/." >> devel.file-list
for file in $(find . \( -iname "*.go" -or -iname "*.s" \) \! -iname "*_test.go" | grep -v "vendor") ; do
    dirprefix=$(dirname $file)
    install -d -p %{buildroot}/%{gopath}/src/github.com/containernetworking/plugins/$dirprefix
    cp -pav $file %{buildroot}/%{gopath}/src/github.com/containernetworking/plugins/$file
    echo "%%{gopath}/src/github.com/containernetworking/plugins/$file" >> devel.file-list

    while [ "$dirprefix" != "." ]; do
        echo "%%dir %%{gopath}/src/github.com/containernetworking/plugins/$dirprefix" >> devel.file-list
        dirprefix=$(dirname $dirprefix)
    done
done

install -d -p %{buildroot}/%{gopath}/src/github.com/containernetworking/plugins/

for file in $(find . -iname "*_test.go" | grep -v "vendor") ; do
    dirprefix=$(dirname $file)
    install -d -p %{buildroot}/%{gopath}/src/github.com/containernetworking/plugins/$dirprefix
    cp -pav $file %{buildroot}/%{gopath}/src/github.com/containernetworking/plugins/$file
    echo "%%{gopath}/src/github.com/containernetworking/plugins/$file" >> unit-test-devel.file-list

    while [ "$dirprefix" != "." ]; do
        echo "%%dir %%{gopath}/src/github.com/containernetworking/plugins/$dirprefix" >> devel.file-list
        dirprefix=$(dirname $dirprefix)
    done
done

sort -u -o devel.file-list devel.file-list

%check
%if 0%(?with_check)
ln -s ./ ./vendor/src
export GOPATH=%{buildroot}/%{gopath}:$(pwd)/vendor:%{gopath}

%gotest github.com/containernetworking/plugins/libcni
%gotest github.com/containernetworking/plugins/pkg/invoke
%gotest github.com/containernetworking/plugins/pkg/ip
%gotest github.com/containernetworking/plugins/pkg/ipam
%gotest github.com/containernetworking/plugins/pkg/ns
%gotest github.com/containernetworking/plugins/pkg/skel
%gotest github.com/containernetworking/plugins/pkg/types
%gotest github.com/containernetworking/plugins/pkg/types/020
%gotest github.com/containernetworking/plugins/pkg/types/current
%gotest github.com/containernetworking/plugins/pkg/utils
%gotest github.com/containernetworking/plugins/pkg/utils/hwaddr
%gotest github.com/containernetworking/plugins/pkg/version
%gotest github.com/containernetworking/plugins/pkg/version/legacy_examples
%gotest github.com/containernetworking/plugins/pkg/version/testhelpers
%gotest github.com/containernetworking/plugins/plugins/ipam/dhcp
%gotest github.com/containernetworking/plugins/plugins/ipam/host-local
%gotest github.com/containernetworking/plugins/plugins/ipam/host-local/backend/allocator
%gotest github.com/containernetworking/plugins/plugins/main/bridge
%gotest github.com/containernetworking/plugins/plugins/main/ipvlan
%gotest github.com/containernetworking/plugins/plugins/main/loopback
%gotest github.com/containernetworking/plugins/plugins/main/macvlan
%gotest github.com/containernetworking/plugins/plugins/main/ptp
%gotest github.com/containernetworking/plugins/plugins/meta/flannel
%gotest github.com/containernetworking/plugins/plugins/test/noop
%endif

%files
%license LICENSE
%doc *.md
%dir %{_libexecdir}/cni
%{_libexecdir}/cni/*

%files devel -f devel.file-list
%license LICENSE
%doc *.md
%dir %{gopath}/src/github.com/containernetworking

%files unit-test-devel -f unit-test-devel.file-list
%license LICENSE
%doc *.md

%changelog
* Wed Nov 20 2019 duyeyu <duyeyu@huawei.com> - 0.8.2-3.git485be65
- Package init
