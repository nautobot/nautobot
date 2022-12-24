import { Fragment } from 'react'
import {Transition, Popover } from '@headlessui/react'
import { NavLink } from "react-router-dom";
import {
    ArrowPathIcon,
    Bars3Icon,
    BookmarkSquareIcon,
    CalendarIcon,
    ChartBarIcon,
    CursorArrowRaysIcon,
    LifebuoyIcon,
    PhoneIcon,
    PlayIcon,
    ShieldCheckIcon,
    Squares2X2Icon,
    XMarkIcon,
    BellIcon,
    PlusIcon,
    CloudArrowDownIcon
} from '@heroicons/react/24/outline'
import { ChevronDownIcon } from '@heroicons/react/20/solid'

import { get_navigation } from '@nautobot/config';




function classNames(...classes) {
    return classes.filter(Boolean).join(' ')
}

const menu_items = get_navigation()


function MenuItems() {
    return (
        <Popover.Group as="nav" className="space-x-7 md:flex items-center ml-10">
            {Object.entries(menu_items).map((main_menu, idx) => (
                <Popover className="relative">
                    {({ open }) => (
                        <>
                            <Popover.Button
                                className={classNames(
                                    open ? 'text-white' : 'text-gray-400',
                                    'group inline-flex items-center rounded-md text-base font-medium hover:text-white'
                                )}
                            >
                                <span className=''>{main_menu[0]}</span>
                                <ChevronDownIcon
                                    className={classNames(
                                        open ? 'text-white' : 'text-gray-400',
                                        'ml-1 h-5 w-5 group-hover:text-white'
                                    )}
                                    aria-hidden="true"
                                />
                            </Popover.Button>

                            <Transition
                                as={Fragment}
                                enter="transition ease-out duration-200"
                                enterFrom="opacity-0 translate-y-1"
                                enterTo="opacity-100 translate-y-0"
                                leave="transition ease-in duration-150"
                                leaveFrom="opacity-100 translate-y-0"
                                leaveTo="opacity-0 translate-y-1"
                            >
                                <Popover.Panel className="absolute mt-3 w-screen max-w-xs transform px-2 lg:left-1/2 lg:-translate-x-1/2">
                                    <div className="overflow-y-auto overflow-x-hidden rounded-lg shadow-lg">
                                        <div className="relative grid bg-gray-800 py-2">
                                            {
                                                main_menu[1].map((group, idx) => (
                                                    <div key={idx} className="mb-3">
                                                        <span className='px-3 text-gray-400 font-light text-sm'>{group.name}</span>
                                                        {group.items.map((item, idx) => (
                                                            <div key={idx} className="justify-between flex items-start rounded-lg px-3 py-2 hover:bg-gray-900">
                                                                <NavLink to={item.path} className="text-gray-300">{item.name}</NavLink>
                                                                <div className="flex gap-1">
                                                                    <PlusIcon className="h-6 w-6 p-1 rounded-md bg-blue-700 text-white" aria-hidden="true" />
                                                                    <CloudArrowDownIcon className="h-6 w-6 p-1 rounded-md bg-green-700 text-white" aria-hidden="true" />
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                ))
                                            }
                                        </div>
                                    </div>
                                </Popover.Panel>
                            </Transition>
                        </>
                    )}
                </Popover>
            ))}

        </Popover.Group>
    )
}

export default function Navigation() {
    return (
        <Popover className="relative">
            <div as="nav" className="bg-gray-800">
                <div className="max-w-full px-8">
                    <div className="relative flex h-16 items-center justify-between">
                        <div className="flex flex-1 items-center justify-center sm:items-stretch sm:justify-start">
                            <div className="flex flex-shrink-0 items-center">
                                <img
                                    className="hidden h-8 w-auto lg:block"
                                    src="./assets/images/nautobot_logo.svg"
                                    alt="Nautobot"
                                />
                            </div>
                            <MenuItems />
                        </div>
                    </div>
                </div>
            </div>
        </Popover>
    )
}
