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
%global built_tag v1.1.1
%global built_tag_strip %(b=%{built_tag}; echo ${b:1})
 
Name: %{project}-%{repo}
Version: 1.1.1
Release: 3
Summary: Libraries for use by writing CNI plugin
License: ASL 2.0
URL: https://github.com/containernetworking/plugins
Source0: https://github.com/containernetworking/plugins/archive/%{built_tag}.tar.gz
Source1: 0001-k3s-cni-adaptation.patch
Source2: https://github.com/zchee/reexec/archive/refs/heads/master.zip
Source3:        sys.tar.gz
BuildRequires: golang >= 1.16.6
BuildRequires: git
BuildRequires: systemd-devel
BuildRequires:  shadow
BuildRequires:  xz
BuildRequires:  unzip
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
%ifarch loongarch64
Patch001:	0001-update-sys-to-support-loong64.patch
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
%ifarch loongarch64
rm -rf vendor/golang.org/x/sys
tar -xf %{SOURCE3} -C vendor/golang.org/x
%endif

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

TMPDIR=$(mktemp -d)
WORKDIR=$TMPDIR/src/github.com/containernetworking/plugins
mkdir -p $WORKDIR
cd ..
cp -r plugins-%{version}/* $WORKDIR
mkdir -p $WORKDIR/vendor/github.com/docker/docker/pkg
unzip -d $WORKDIR/vendor/github.com/docker/docker/pkg/ %{SOURCE2}
mv $WORKDIR/vendor/github.com/docker/docker/pkg/reexec-master $WORKDIR/vendor/github.com/docker/docker/pkg/reexec

cd $WORKDIR
cp %{SOURCE1} ./
patch -p1 < 0001-k3s-cni-adaptation.patch
cat > main.go << EOF
package main

import (
        "os"
        "path/filepath"

        "github.com/containernetworking/plugins/plugins/ipam/host-local"
        "github.com/containernetworking/plugins/plugins/main/bridge"
        "github.com/containernetworking/plugins/plugins/main/loopback"
        //"github.com/containernetworking/plugins/plugins/meta/flannel"
        "github.com/containernetworking/plugins/plugins/meta/portmap"
        "github.com/docker/docker/pkg/reexec"
)

func main() {
        os.Args[0] = filepath.Base(os.Args[0])
        reexec.Register("host-local", hostlocal.Main)
        reexec.Register("bridge", bridge.Main)
        //reexec.Register("flannel", flannel.Main)
        reexec.Register("loopback", loopback.Main)
        reexec.Register("portmap", portmap.Main)
        reexec.Init()
}
EOF

PKG="github.com/k3s-io/k3s"
PKG_CONTAINERD="github.com/containerd/containerd"
PKG_K3S_CONTAINERD="github.com/k3s-io/containerd"
PKG_CRICTL="github.com/kubernetes-sigs/cri-tools/pkg"
PKG_K8S_BASE="k8s.io/component-base"
PKG_K8S_CLIENT="k8s.io/client-go/pkg"
PKG_CNI_PLUGINS="github.com/containernetworking/plugins"

buildDate=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

VERSIONFLAGS="
    -X ${PKG}/pkg/version.Version=${VERSION}
    -X ${PKG}/pkg/version.GitCommit=${COMMIT:0:8}

    -X ${PKG_K8S_CLIENT}/version.gitVersion=${VERSION}
    -X ${PKG_K8S_CLIENT}/version.gitCommit=${COMMIT}
    -X ${PKG_K8S_CLIENT}/version.gitTreeState=${TREE_STATE}
    -X ${PKG_K8S_CLIENT}/version.buildDate=${buildDate}

    -X ${PKG_K8S_BASE}/version.gitVersion=${VERSION}
    -X ${PKG_K8S_BASE}/version.gitCommit=${COMMIT}
    -X ${PKG_K8S_BASE}/version.gitTreeState=${TREE_STATE}
    -X ${PKG_K8S_BASE}/version.buildDate=${buildDate}

    -X ${PKG_CRICTL}/version.Version=${VERSION_CRICTL}

    -X ${PKG_CONTAINERD}/version.Version=${VERSION_CONTAINERD}
    -X ${PKG_CONTAINERD}/version.Package=${PKG_K3S_CONTAINERD}
"
TAGS="apparmor seccomp netcgo osusergo providerless"
STATIC="-extldflags '-static -lm -ldl -lz -lpthread'"
GO111MODULE=off CGO_ENABLED=0 GOPATH=$TMPDIR go build -tags "$TAGS" -ldflags "$VERSIONFLAGS $LDFLAGS $STATIC" -o %{_builddir}/cni
 
%install
install -d -p %{buildroot}%{_libexecdir}/cni/
install -p -m 0755 bin/* %{buildroot}/%{_libexecdir}/cni
cp %{_builddir}/cni %{buildroot}%{_libexecdir}/cni/
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
* Tue Feb 7 2023 Wenlong Zhang <zhangwenlong@loongson.cn> - 1.1.1-3
- update sys to support loongarch64

* Mon Jan 9 2023 huajingyun <huajingyun@loongson.cn> - 1.1.1-2
- add loong64 support

* Wed Jul 20 2022 Ge Wang <wangge20@h-partners.com> - 1.1.1-1
- update to version 1.1.1

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
