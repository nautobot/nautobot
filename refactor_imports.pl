#!/usr/bin/env perl

use warnings;
use strict;

use Data::Dumper;
use File::Copy;

my $file = $ARGV[0];

# skip __init__.py files
if ($file =~ /__init__\.py/){
    exit;
}

if (not -f $file){
    die("$file is not a valid file path");
}

my @python_path = split(/\//, $file);
if ($python_path[0] !~ /^nautobot$/i){
    die("must be run from nautobot repo root");
}
pop(@python_path);
my $full_python_path = join(".", @python_path);



open(my $fh, "<", $file) or die $!;

my $imports = {};
my $module_replacements = {};
my $name_replacements = {};

# loop through input and find import lines
for my $line (<$fh>){
    if ($line =~ /^\s*from (\S+) import (.*)$/){
        my ($module, $names) = ($1, $2);
        # special handling of "from . import foo"
        if ($module eq "."){
            chomp($line);
            my $old_name = "^\Q$line\E\$";
            my $new_name = "from $full_python_path import $names";
            $module_replacements->{$old_name} = $new_name;
        } elsif ($names eq "*"){ # don't touch wildcard imports
            print("wildcard import found in $file\n");
            next;
        } elsif ($names =~ /\(/) { # this script isn't ambitious enough for multi-line imports yet
            print("multi-line import found in $file\n");
            next;
        } else {
            $imports->{$module} = $names;
        }
    }
}

# loop through imports and build regular expressions
for my $module (keys(%$imports)){
    my $names = $imports->{$module};

    # convert relative imports to absolute
    if ($module =~ /^\.(.*)/){
        my $module_name = $1;
        my $import_path = $full_python_path;

        # multi-level relative imports
        if ($module_name =~ /\./){
            my @parts = split(/\./, $module_name);
            $module_name = pop(@parts);
            $import_path .= "." . join(".", @parts);
        }

        # fix names
        for my $name (split(/,\s*/, $imports->{$module})){
            $name_replacements->{$name} = "$module_name.$name";
        }

        # fix imports
        my $old_name = "^from \Q$module\E import .*";
        my $new_name = "from $import_path import $module_name";
        $module_replacements->{$old_name} = $new_name;
    }
}
# print(Dumper($imports));
# print(Dumper($module_replacements));
# print(Dumper($name_replacements));


seek($fh, 0, 0);
open(my $fh_out, ">", "$file.new") or die $!;
while (<$fh>){
    my $line = $_;
    for my $old_name (keys(%$module_replacements)){
        my $new_name = $module_replacements->{$old_name};
        $line =~ s/$old_name/$new_name/g;
    }
    if ($line !~ /^\s*(import|from) /){
        for my $old_name (keys(%$name_replacements)){
            my $new_name = $name_replacements->{$old_name};
            $line =~ s/\Q$old_name\E/$new_name/g;
        }
    }
    print $fh_out $line;
}
close($fh_out);

close($fh);
move("$file.new", $file);
