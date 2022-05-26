%global with_devel 1
%global with_bundled 1
%global with_check 0
%global with_unit_test 1
 
%global debug_package   %{nil}

%global project containernetworking
%global repo plugins
%global import_path github.com/%{project}/%{repo}
 
# Used for comparing with latest upstream tag
# to decide whether to autobuild
%global built_tag v1.0.1
%global built_tag_strip %(b=%{built_tag}; echo ${b:1})
 
Name: %{project}-%{repo}
Version: 1.0.1
Release: 2
Summary: Libraries for use by writing CNI plugin
License: ASL 2.0
URL: https://github.com/containernetworking/plugins
Source0: https://github.com/containernetworking/plugins/archive/%{built_tag}.tar.gz

BuildRequires: golang >= 1.16.6
BuildRequires: git
BuildRequires: systemd-devel
Requires: systemd
 
%if ! 0%{?with_bundled}
BuildRequires: go-bindata
BuildRequires: golang(github.com/vishvananda/netlink)
BuildRequires: golang(github.com/coreos/go-systemd/activation)
BuildRequires: golang(github.com/d2g/dhcp4)
BuildRequires: golang(github.com/d2g/dhcp4client)
BuildRequires: golang(github.com/vishvananda/netlink)
BuildRequires: golang(golang.org/x/sys/unix)
BuildRequires: golang(github.com/coreos/go-iptables/iptables)
%endif
 
Obsoletes: %{project}-cni < 0.7.1-2
Provides: %{project}-cni = %{version}-%{release}
Provides: kubernetes-cni
 
%description
The CNI (Container Network Interface) project consists of a specification
and libraries for writing plugins to configure network interfaces in Linux
containers, along with a number of supported plugins. CNI concerns itself
only with network connectivity of containers and removing allocated resources
when the container is deleted.
 
%if 0%{?with_devel}
%package devel
Summary: %{summary}
BuildArch: noarch
 
%if 0%{?with_check} && ! 0%{?with_bundled}
BuildRequires: golang(github.com/coreos/go-iptables/iptables)
BuildRequires: golang(github.com/vishvananda/netlink)
BuildRequires: golang(golang.org/x/sys/unix)
%endif
 
%description devel
This package contains library source intended for
building other packages which use import path with
%{import_path} prefix.
%endif
 
%if 0%{?with_unit_test} && 0%{?with_devel}
%package unit-test-devel
Summary: Unit tests for %{name} package
%if 0%{?with_check}
%endif
 
Requires: %{name}-devel = %{version}-%{release}
 
%if 0%{?with_check} && ! 0%{?with_bundled}
BuildRequires: golang(github.com/d2g/dhcp4)
BuildRequires: golang(github.com/onsi/ginkgo)
BuildRequires: golang(github.com/onsi/ginkgo/config)
BuildRequires: golang(github.com/onsi/ginkgo/extensions/table)
BuildRequires: golang(github.com/onsi/gomega)
BuildRequires: golang(github.com/onsi/gomega/gbytes)
BuildRequires: golang(github.com/onsi/gomega/gexec)
BuildRequires: golang(github.com/vishvananda/netlink/nl)
%endif
 
%description unit-test-devel
This package contains unit tests for project
providing packages with %{import_path} prefix.
%endif
 
%prep
%autosetup -Sgit -n %{repo}-%{built_tag_strip}
rm -rf plugins/main/windows
 
# Use correct paths in cni-dhcp unitfiles
sed -i 's/\/opt\/cni\/bin/\%{_prefix}\/libexec\/cni/' plugins/ipam/dhcp/systemd/cni-dhcp.service
 
%build
export ORG_PATH="github.com/%{project}"
export REPO_PATH="$ORG_PATH/%{repo}"
 
if [ ! -h gopath/src/${REPO_PATH} ]; then
    mkdir -p gopath/src/${ORG_PATH}
    ln -s ../../../.. gopath/src/${REPO_PATH} || exit 255
fi
 
export GOPATH=$(pwd)/gopath
mkdir -p $(pwd)/bin
export GO111MODULE=off
 
echo "Building plugins"
export PLUGINS="plugins/meta/* plugins/main/* plugins/ipam/* plugins/sample"
for d in $PLUGINS; do
    if [ -d "$d" ]; then
        plugin="$(basename "$d")"
        echo "  $plugin"
        go build -buildmode pie -compiler gc -tags="rpm_crashtraceback ${BUILDTAGS:-}" -ldflags "${LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d '  \n') -extldflags '%__global_ldflags %{?__golang_extldflags}'" -a -v -x -o "${PWD}/bin/$plugin" "$@" github.com/containernetworking/plugins/$d
    fi
done
 
%install
install -d -p %{buildroot}%{_libexecdir}/cni/
install -p -m 0755 bin/* %{buildroot}/%{_libexecdir}/cni
install -d -p     %{buildroot}/%{gopath}/src/github.com/containernetworking/plugins/
 
install -dp %{buildroot}%{_unitdir}
install -p plugins/ipam/dhcp/systemd/cni-dhcp.service %{buildroot}%{_unitdir}
install -p plugins/ipam/dhcp/systemd/cni-dhcp.socket %{buildroot}%{_unitdir}
 
# source codes for building projects
%if 0%{?with_devel}
install -d -p %{buildroot}/%{gopath}/src/%{import_path}/
echo "%%dir %%{gopath}/src/%%{import_path}/." >> devel.file-list
# find all *.go but no *_test.go files and generate devel.file-list
for file in $(find . \( -iname "*.go" -or -iname "*.s" \) \! -iname "*_test.go" | grep -v "vendor") ; do
    dirprefix=$(dirname $file)
    install -d -p %{buildroot}/%{gopath}/src/%{import_path}/$dirprefix
    cp -pav $file %{buildroot}/%{gopath}/src/%{import_path}/$file
    echo "%%{gopath}/src/%%{import_path}/$file" >> devel.file-list
 
    while [ "$dirprefix" != "." ]; do
        echo "%%dir %%{gopath}/src/%%{import_path}/$dirprefix" >> devel.file-list
        dirprefix=$(dirname $dirprefix)
    done
done
%endif
 
# testing files for this project
%if 0%{?with_unit_test} && 0%{?with_devel}
install -d -p %{buildroot}/%{gopath}/src/%{import_path}/
# find all *_test.go files and generate unit-test-devel.file-list
for file in $(find . -iname "*_test.go" | grep -v "vendor") ; do
    dirprefix=$(dirname $file)
    install -d -p %{buildroot}/%{gopath}/src/%{import_path}/$dirprefix
    cp -pav $file %{buildroot}/%{gopath}/src/%{import_path}/$file
    echo "%%{gopath}/src/%%{import_path}/$file" >> unit-test-devel.file-list
 
    while [ "$dirprefix" != "." ]; do
        echo "%%dir %%{gopath}/src/%%{import_path}/$dirprefix" >> devel.file-list
        dirprefix=$(dirname $dirprefix)
    done
done
%endif
 
%if 0%{?with_devel}
sort -u -o devel.file-list devel.file-list
%endif
 
%check
%if 0%{?with_check} && 0%{?with_unit_test} && 0%{?with_devel}
%if ! 0%{?with_bundled}
export GOPATH=%{buildroot}/%{gopath}:%{gopath}
%else
# Since we aren't packaging up the vendor directory we need to link
# back to it somehow. Hack it up so that we can add the vendor
# directory from BUILD dir as a gopath to be searched when executing
# tests from the BUILDROOT dir.
ln -s ./ ./vendor/src # ./vendor/src -> ./vendor
 
export GOPATH=%{buildroot}/%{gopath}:$(pwd)/vendor:%{gopath}
%endif
 
%if ! 0%{?gotest:1}
%global gotest go test
%endif
 
%gotest %{import_path}/libcni
%gotest %{import_path}/pkg/invoke
%gotest %{import_path}/pkg/ip
%gotest %{import_path}/pkg/ipam
%gotest %{import_path}/pkg/ns
%gotest %{import_path}/pkg/skel
%gotest %{import_path}/pkg/types
%gotest %{import_path}/pkg/types/020
%gotest %{import_path}/pkg/types/current
%gotest %{import_path}/pkg/utils
%gotest %{import_path}/pkg/utils/hwaddr
%gotest %{import_path}/pkg/version
%gotest %{import_path}/pkg/version/legacy_examples
%gotest %{import_path}/pkg/version/testhelpers
%gotest %{import_path}/plugins/ipam/dhcp
%gotest %{import_path}/plugins/ipam/host-local
%gotest %{import_path}/plugins/ipam/host-local/backend/allocator
%gotest %{import_path}/plugins/main/bridge
%gotest %{import_path}/plugins/main/ipvlan
%gotest %{import_path}/plugins/main/loopback
%gotest %{import_path}/plugins/main/macvlan
%gotest %{import_path}/plugins/main/ptp
%gotest %{import_path}/plugins/meta/flannel
%gotest %{import_path}/plugins/test/noop
%endif
 
#define license tag if not already defined
%{!?_licensedir:%global license %doc}
 
%files
%license LICENSE
%doc *.md
%dir %{_libexecdir}/cni
%{_libexecdir}/cni/*
%{_unitdir}/cni-dhcp.service
%{_unitdir}/cni-dhcp.socket
 
%if 0%{?with_devel}
%files devel -f devel.file-list
%license LICENSE
%doc *.md
%dir %{gopath}/src/github.com/%{project}
%endif
 
%if 0%{?with_unit_test} && 0%{?with_devel}
%files unit-test-devel -f unit-test-devel.file-list
%license LICENSE
%doc *.md
%endif


%changelog
* Mon Jan 10 2022 liyanan <liyanan32@huawei.com> - 1.0.1-2
- drop deps for golang packages due to vendor has everything

* Fri Dec 10 2021 haozi007 <liuhao27@huawei.com> - 1.0.1-1
- Type:sync
- ID:NA
- SUG:NA
- DESC: update to 1.0.1

* Mon Feb  8 2021 lingsheng <lingsheng@huawei.com> - 0.8.2-4.git485be65
- Change BuildRequires to golang

* Wed Nov 20 2019 duyeyu <duyeyu@huawei.com> - 0.8.2-3.git485be65
- Package init
